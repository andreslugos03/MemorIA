"""Registro de correcciones comunitarias (requisito 5 del asistente).

Las comunidades pueden proponer correcciones sobre un documento, un
fragmento, una entrada del léxico o una respuesta. Cada propuesta y cada
resolución queda como una línea nueva de un archivo JSONL que nunca se
reescribe. Cada línea lleva fecha, autoría colectiva y el resumen SHA-256 de
la línea anterior, de modo que cualquier alteración posterior del historial
se detecta con `verificar`.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass

from ..util import ahora_utc, sha256

CATEGORIAS = ("lexico", "hecho", "atribucion", "cuidado", "procedencia", "otra")
OBJETOS = ("documento", "fragmento", "lexico", "respuesta")
ESTADOS = ("aceptada", "rechazada")
CAMPOS_LEXICO = ("hablante", "epoca", "nota", "categoria")
GENESIS = "0" * 64

_cerrojo = threading.Lock()


class ErrorCorreccion(ValueError):
    pass


def _huella(entrada: dict) -> str:
    sin_hash = {k: v for k, v in entrada.items() if k != "hash"}
    return sha256(json.dumps(sin_hash, ensure_ascii=False, sort_keys=True))


@dataclass
class EstadoCorreccion:
    propuesta: dict
    resolucion: dict | None

    @property
    def estado(self) -> str:
        return self.resolucion["estado"] if self.resolucion else "propuesta"


class RegistroCorrecciones:
    def __init__(self, ruta: str):
        self.ruta = ruta

    def entradas(self) -> list[dict]:
        if not os.path.exists(self.ruta):
            return []
        with open(self.ruta, encoding="utf-8") as f:
            return [json.loads(linea) for linea in f if linea.strip()]

    def _anexar(self, entrada: dict) -> dict:
        with _cerrojo:
            previas = self.entradas()
            entrada["hash_anterior"] = previas[-1]["hash"] if previas else GENESIS
            entrada["hash"] = _huella(entrada)
            os.makedirs(os.path.dirname(os.path.abspath(self.ruta)), exist_ok=True)
            with open(self.ruta, "a", encoding="utf-8") as f:
                f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
        return entrada

    def proponer(self, autoria_colectiva: str, objeto_tipo: str, objeto_id: str, categoria: str,
                 texto_propuesto: str, justificacion: str = "", campo: str = "", texto_actual: str = "") -> dict:
        if not autoria_colectiva.strip():
            raise ErrorCorreccion("La corrección necesita una autoría colectiva (organización, colectivo o comunidad)")
        if objeto_tipo not in OBJETOS:
            raise ErrorCorreccion(f"Tipo de objeto '{objeto_tipo}' no válido. Opciones: {', '.join(OBJETOS)}")
        if categoria not in CATEGORIAS:
            raise ErrorCorreccion(f"Categoría '{categoria}' no válida. Opciones: {', '.join(CATEGORIAS)}")
        if not texto_propuesto.strip():
            raise ErrorCorreccion("La corrección necesita un texto propuesto")
        if objeto_tipo == "lexico" and campo and campo not in CAMPOS_LEXICO:
            raise ErrorCorreccion(f"Campo de léxico '{campo}' no válido. Opciones: {', '.join(CAMPOS_LEXICO)}")
        n = sum(1 for e in self.entradas() if e["tipo"] == "propuesta") + 1
        return self._anexar({
            "tipo": "propuesta", "id": f"CORR-{n:04d}", "fecha_utc": ahora_utc(),
            "autoria_colectiva": autoria_colectiva.strip(), "objeto": {"tipo": objeto_tipo, "id": objeto_id.strip()},
            "categoria": categoria, "campo": campo, "texto_actual": texto_actual, "texto_propuesto": texto_propuesto.strip(),
            "justificacion": justificacion.strip(),
        })

    def resolver(self, id_correccion: str, estado: str, autoria: str, motivo: str = "") -> dict:
        if estado not in ESTADOS:
            raise ErrorCorreccion(f"Estado '{estado}' no válido. Opciones: {', '.join(ESTADOS)}")
        if not autoria.strip():
            raise ErrorCorreccion("La resolución necesita autoría (por ejemplo, el panel de validación)")
        actual = {c.propuesta["id"]: c for c in self.estado_actual()}
        if id_correccion not in actual:
            raise ErrorCorreccion(f"No existe la corrección {id_correccion}")
        return self._anexar({"tipo": "resolucion", "ref": id_correccion, "fecha_utc": ahora_utc(),
                             "estado": estado, "autoria_colectiva": autoria.strip(), "motivo": motivo.strip()})

    def estado_actual(self) -> list[EstadoCorreccion]:
        propuestas, resoluciones = {}, {}
        for e in self.entradas():
            if e["tipo"] == "propuesta":
                propuestas[e["id"]] = e
            elif e["tipo"] == "resolucion":
                resoluciones[e["ref"]] = e  # la última resolución prevalece y la anterior queda en el historial
        return [EstadoCorreccion(p, resoluciones.get(i)) for i, p in propuestas.items()]

    def aceptadas(self) -> list[dict]:
        return [c.propuesta for c in self.estado_actual() if c.estado == "aceptada"]

    def verificar(self) -> tuple[bool, list[str]]:
        problemas, anterior = [], GENESIS
        for i, e in enumerate(self.entradas(), start=1):
            if e.get("hash_anterior") != anterior:
                problemas.append(f"línea {i}: la cadena se rompe (hash_anterior no coincide)")
            if _huella(e) != e.get("hash"):
                problemas.append(f"línea {i}: el contenido fue alterado después de registrarse")
            anterior = e.get("hash", "")
        return not problemas, problemas
