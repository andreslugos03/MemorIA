"""Compuertas éticas que deciden qué contenido puede salir hacia cada sistema.

Primera compuerta (por metadatos). Las fuentes restringidas y embargadas solo
se entregan a sistemas de pesos abiertos que corren en infraestructura local.
Un sistema cuenta como local cuando lo declara su configuración y además su
dirección es localhost; la declaración sola no basta.

Segunda compuerta (por contenido). Antes de que cualquier texto salga hacia un
sistema externo se compara con las fuentes no públicas del corpus. Si comparte
ocho palabras seguidas con alguna de ellas, la consulta queda retenida y el
motivo se registra. Esta compuerta cubre el error humano de marcación que la
primera no ve, por ejemplo un ítem marcado como público cuyo texto proviene de
un testimonio restringido.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from .corpus import Documento
from .util import ngramas, tokens

N_PALABRAS = 8
HOSTS_LOCALES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


@dataclass
class Decision:
    permitido: bool
    motivo: str = ""
    documentos: list[str] = field(default_factory=list)


def es_local(sistema: dict) -> bool:
    """Un sistema es local si su configuración lo declara y su dirección lo confirma."""
    if not sistema.get("local", False):
        return False
    if sistema.get("proveedor") == "simulado":
        return True
    host = (urlparse(sistema.get("base_url", "")).hostname or "").lower()
    return host in HOSTS_LOCALES


def niveles_permitidos(sistema: dict, contexto: str = "auditoria") -> set[str]:
    """Niveles de acceso que puede recuperar un sistema.

    En la interfaz pública solo circulan fuentes públicas, también cuando el modelo
    corre en un computador local. La corrida de demostración de octubre de 2026
    mostró que un sistema local con acceso a fuentes restringidas las filtraba
    en sus respuestas, y esa evidencia fijó esta regla.
    """
    if contexto == "publico":
        return {"publica"}
    if es_local(sistema):
        return {"publica", "restringida", "embargada"}
    return {"publica"}


class CompuertaContenido:
    def __init__(self, documentos: list[Documento], n: int = N_PALABRAS):
        self.n = n
        self._indice: dict[tuple[str, ...], set[str]] = {}
        for d in documentos:
            if d.publico:
                continue
            for g in ngramas(tokens(d.texto), n):
                self._indice.setdefault(g, set()).add(d.id)

    def coincidencias(self, texto: str) -> list[str]:
        docs: set[str] = set()
        for g in ngramas(tokens(texto), self.n):
            docs |= self._indice.get(g, set())
        return sorted(docs)

    def revisar(self, sistema: dict, texto_saliente: str, nivel_item: str = "publica") -> Decision:
        if es_local(sistema):
            return Decision(True, "sistema local")
        nivel_item = (nivel_item or "publica").lower()
        if any(n in nivel_item for n in ("restringida", "embargada")):
            return Decision(False, f"ítem con fuentes de nivel {nivel_item}; solo un sistema local puede procesarlo")
        docs = self.coincidencias(texto_saliente)
        if docs:
            return Decision(
                False,
                f"el texto comparte {self.n} palabras seguidas con fuentes no públicas ({', '.join(docs)})",
                docs,
            )
        return Decision(True, "sin coincidencias con fuentes no públicas")
