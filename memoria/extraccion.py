"""Extracciones automáticas sobre las respuestas.

Solo cubren lo que el protocolo permite automatizar sin juicio humano
(entidades frente al estándar de oro, menciones municipales, citas emitidas) y
sugerencias que el codificador siempre verifica (filtración, tipos de fuente).
"""
from __future__ import annotations

import json
import re
from collections import Counter

from .compuertas import CompuertaContenido
from .util import sin_tildes

_CITA = re.compile(r"\[([^\[\]\s]+#\d+)\]")


def citas(respuesta: str) -> list[str]:
    vistas = []
    for c in _CITA.findall(respuesta or ""):
        if c not in vistas:
            vistas.append(c)
    return vistas


def entidades_desde_respuesta(respuesta: str, texto_fragmento: str) -> list[dict]:
    """Interpreta la lista JSON de entidades y calcula sus desplazamientos.

    Tolera texto alrededor de la lista. Una entidad que no aparece de forma
    literal en el fragmento se descarta, porque no puede alinearse con el
    estándar de oro.
    """
    m = re.search(r"\[.*\]", respuesta or "", flags=re.DOTALL)
    if not m:
        return []
    try:
        lista = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    salida, usados = [], set()
    for e in lista if isinstance(lista, list) else []:
        if not isinstance(e, dict):
            continue
        texto, tipo = str(e.get("texto", "")).strip(), str(e.get("tipo", "")).strip().upper()
        if not texto or not tipo:
            continue
        inicio = texto_fragmento.find(texto)
        while inicio != -1 and (inicio, tipo) in usados:
            inicio = texto_fragmento.find(texto, inicio + 1)
        if inicio == -1:
            continue
        usados.add((inicio, tipo))
        salida.append({"inicio": inicio, "fin": inicio + len(texto), "tipo": tipo, "texto": texto})
    return salida


def _clave_municipio(nombre: str) -> str:
    return sin_tildes(nombre.lower())


def menciones_municipales(respuesta: str, municipios: list[str]) -> Counter:
    """Cuenta menciones de cada municipio de la referencia, sin distinguir tildes."""
    texto = sin_tildes((respuesta or "").lower())
    conteo = Counter()
    for m in sorted(municipios, key=len, reverse=True):
        patron = r"(?<![a-z0-9])" + re.escape(_clave_municipio(m)) + r"(?![a-z0-9])"
        n = len(re.findall(patron, texto))
        if n:
            conteo[m] += n
            texto = re.sub(patron, " ", texto)  # evita contar subcadenas de nombres más largos
    return conteo


def sugerencia_filtracion(respuesta: str, compuerta: CompuertaContenido) -> list[str]:
    """Documentos no públicos con los que la respuesta comparte ocho palabras seguidas."""
    return compuerta.coincidencias(respuesta or "")
