"""Corpus documental y léxico regional.

Cada documento declara su tipo de fuente, su fecha, su municipio, su autoría
o hablante y su nivel de acceso. Esos metadatos gobiernan qué puede leer cada
sistema (compuertas éticas) y qué procedencia muestra el asistente.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from .util import ErrorDatos, es_verdadero, leer_csv, tokens

TIPOS_FUENTE = ("testimonial", "judicial", "institucional", "prensa")
NIVELES_ACCESO = ("publica", "restringida", "embargada")


@dataclass
class Documento:
    id: str
    titulo: str
    tipo_fuente: str
    fecha: str
    municipio: str
    nivel_acceso: str
    texto: str
    autoria: str = ""
    consentimiento_ia: bool = True
    hechos: list[dict] = field(default_factory=list)
    personas: list[dict] = field(default_factory=list)
    referencia: str = ""

    @property
    def publico(self) -> bool:
        return self.nivel_acceso == "publica"

    def victimas(self) -> list[str]:
        return [p["nombre"] for p in self.personas if p.get("rol", "").lower() == "victima" and p.get("nombre")]


@dataclass
class Fragmento:
    id: str
    documento: Documento
    texto: str
    posicion: int

    @property
    def nivel_acceso(self) -> str:
        return self.documento.nivel_acceso

    def ficha(self) -> str:
        d = self.documento
        return f"{d.titulo} · {d.tipo_fuente} · {d.fecha} · {d.municipio}"


@dataclass
class EntradaLexico:
    termino: str
    variantes: list[str]
    hablante: str
    epoca: str
    categoria: str
    estigmatizante: bool
    nota: str = ""

    def formas(self) -> list[str]:
        return [self.termino] + [v for v in self.variantes if v]


def _documento_desde_dict(d: dict, origen: str) -> Documento:
    faltan = [c for c in ("id", "titulo", "tipo_fuente", "fecha", "nivel_acceso", "texto") if not str(d.get(c, "")).strip()]
    if faltan:
        raise ErrorDatos(f"{origen}: documento {d.get('id', '?')} sin {', '.join(faltan)}")
    tipo = str(d["tipo_fuente"]).strip().lower()
    nivel = str(d["nivel_acceso"]).strip().lower().replace("ú", "u")
    if tipo not in TIPOS_FUENTE:
        raise ErrorDatos(f"{origen}: tipo_fuente '{tipo}' en {d['id']} no es uno de {', '.join(TIPOS_FUENTE)}")
    if nivel not in NIVELES_ACCESO:
        raise ErrorDatos(f"{origen}: nivel_acceso '{nivel}' en {d['id']} no es uno de {', '.join(NIVELES_ACCESO)}")

    def lista(valor):
        if isinstance(valor, list):
            return valor
        if isinstance(valor, str) and valor.strip():
            return json.loads(valor)
        return []

    consentimiento = d.get("consentimiento_ia", None)
    if consentimiento in (None, ""):
        # Por prudencia, un testimonio sin registro de consentimiento no entra a la IA.
        consentimiento = tipo != "testimonial"
    elif not isinstance(consentimiento, bool):
        consentimiento = es_verdadero(consentimiento)

    return Documento(
        id=str(d["id"]).strip(),
        titulo=str(d["titulo"]).strip(),
        tipo_fuente=tipo,
        fecha=str(d["fecha"]).strip(),
        municipio=str(d.get("municipio", "")).strip(),
        nivel_acceso=nivel,
        texto=str(d["texto"]).strip(),
        autoria=str(d.get("autoria", "")).strip(),
        consentimiento_ia=bool(consentimiento),
        hechos=lista(d.get("hechos")),
        personas=lista(d.get("personas")),
        referencia=str(d.get("referencia", "")).strip(),
    )


def cargar_documentos(ruta: str) -> list[Documento]:
    """Carga el corpus desde JSONL (un documento por línea) o CSV."""
    if not os.path.exists(ruta):
        raise ErrorDatos(f"No existe el corpus {ruta}")
    docs: list[Documento] = []
    if ruta.endswith(".csv"):
        for i, fila in enumerate(leer_csv(ruta), start=2):
            docs.append(_documento_desde_dict(fila, f"{os.path.basename(ruta)} fila {i}"))
    else:
        with open(ruta, encoding="utf-8-sig") as f:
            for i, linea in enumerate(f, start=1):
                if not linea.strip():
                    continue
                try:
                    d = json.loads(linea)
                except json.JSONDecodeError as e:
                    raise ErrorDatos(f"{os.path.basename(ruta)} línea {i}: JSON inválido ({e.msg})") from e
                docs.append(_documento_desde_dict(d, f"{os.path.basename(ruta)} línea {i}"))
    vistos = set()
    for d in docs:
        if d.id in vistos:
            raise ErrorDatos(f"Identificador de documento repetido: {d.id}")
        vistos.add(d.id)
    return docs


def fragmentar(doc: Documento, tamano: int = 120, solapamiento: int = 30) -> list[Fragmento]:
    """Divide un documento en fragmentos de `tamano` palabras con solapamiento.

    Los cortes respetan los límites de oración cuando es posible, para que
    cada fragmento citado conserve sentido completo.
    """
    oraciones = re.split(r"(?<=[.!?])\s+", doc.texto)
    fragmentos, actual, n_actual = [], [], 0
    for o in oraciones:
        n = len(o.split())
        if actual and n_actual + n > tamano:
            fragmentos.append(" ".join(actual))
            # solapamiento: conserva las últimas oraciones hasta ~solapamiento palabras
            cola, n_cola = [], 0
            for prev in reversed(actual):
                if n_cola >= solapamiento:
                    break
                cola.insert(0, prev)
                n_cola += len(prev.split())
            actual, n_actual = (cola, n_cola) if n_cola < tamano else ([], 0)
        actual.append(o)
        n_actual += n
    if actual:
        fragmentos.append(" ".join(actual))
    return [Fragmento(f"{doc.id}#{i}", doc, t, i) for i, t in enumerate(fragmentos)]


def cargar_lexico(ruta: str) -> list[EntradaLexico]:
    filas = leer_csv(ruta, obligatorias=("termino",))
    salida = []
    for f in filas:
        salida.append(EntradaLexico(
            termino=f["termino"],
            variantes=[v.strip() for v in f.get("variantes", "").split(";") if v.strip()],
            hablante=f.get("hablante", ""),
            epoca=f.get("epoca", ""),
            categoria=f.get("categoria", ""),
            estigmatizante=es_verdadero(f.get("estigmatizante", "0")),
            nota=f.get("nota", ""),
        ))
    return salida


def buscar_termino(texto: str, entrada: EntradaLexico) -> list[tuple[int, int, str]]:
    """Ubica las apariciones de un término o sus variantes sin distinguir
    mayúsculas. Devuelve (inicio, fin, forma) sobre el texto original."""
    hallazgos = []
    for forma in entrada.formas():
        patron = r"(?<![\wáéíóúñ])" + r"\s+".join(re.escape(p) for p in forma.split()) + r"(?![\wáéíóúñ])"
        for m in re.finditer(patron, texto, flags=re.IGNORECASE):
            hallazgos.append((m.start(), m.end(), m.group(0)))
    # elimina solapes, prefiere la forma más larga
    hallazgos.sort(key=lambda h: (h[0], -(h[1] - h[0])))
    limpios, fin = [], -1
    for h in hallazgos:
        if h[0] >= fin:
            limpios.append(h)
            fin = h[1]
    return limpios


def contiene_terminos(texto: str, terminos: list[str]) -> int:
    toks = " ".join(tokens(texto))
    return sum(1 for t in terminos if " ".join(tokens(t)) and f" {' '.join(tokens(t))} " in f" {toks} ")
