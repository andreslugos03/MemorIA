"""Utilidades compartidas: lectura robusta de CSV, números con coma decimal,
normalización de texto en español, n-gramas y resúmenes criptográficos."""
from __future__ import annotations

import csv
import hashlib
import io
import os
import re
import unicodedata
from datetime import datetime, timezone
from typing import Iterable

DELIMITADORES = ",;\t"


class ErrorDatos(ValueError):
    """Error de formato en un archivo de datos del proyecto."""


def _decodificar(crudo: bytes) -> tuple[str, str]:
    for codificacion in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return crudo.decode(codificacion), codificacion
        except UnicodeDecodeError:
            continue
    raise ErrorDatos("No se pudo decodificar el archivo")  # pragma: no cover


def detectar_delimitador(texto: str) -> str:
    """Detecta coma, punto y coma o tabulador a partir del encabezado.

    Excel en configuración regional de Colombia y España guarda los CSV con
    punto y coma. Leerlos con coma produce una sola columna sin aviso.
    """
    primera = texto.split("\n", 1)[0]
    conteos = {d: primera.count(d) for d in DELIMITADORES}
    mejor = max(conteos, key=conteos.get)
    return mejor if conteos[mejor] > 0 else ","


def leer_csv(ruta: str | os.PathLike, obligatorias: Iterable[str] = ()) -> list[dict]:
    """Lee un CSV y devuelve una lista de diccionarios con claves y valores limpios.

    Acepta UTF-8 con o sin BOM y Windows-1252, y separadores coma, punto y coma
    o tabulador. Si faltan columnas obligatorias lanza ErrorDatos con el nombre
    del archivo y las columnas ausentes. Un archivo inexistente devuelve [].
    """
    if not os.path.exists(ruta):
        return []
    with open(ruta, "rb") as f:
        texto, _ = _decodificar(f.read())
    if not texto.strip():
        return []
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    lector = csv.DictReader(io.StringIO(texto), delimiter=detectar_delimitador(texto))
    columnas = [c.strip() for c in (lector.fieldnames or []) if c]
    faltan = [c for c in obligatorias if c not in columnas]
    if faltan:
        raise ErrorDatos(f"{os.path.basename(str(ruta))}: faltan columnas {', '.join(faltan)}")
    filas = []
    for fila in lector:
        limpia = {}
        for k, v in fila.items():
            if not k:
                continue
            if isinstance(v, list):  # columnas sobrantes
                v = ",".join(v)
            limpia[k.strip()] = v.strip() if isinstance(v, str) else ("" if v is None else v)
        if any(str(v) for v in limpia.values()):
            filas.append(limpia)
    return filas


def escribir_csv(ruta: str | os.PathLike, filas: list[dict], columnas: list[str] | None = None) -> None:
    """Escribe en UTF-8 con BOM para que Excel reconozca las tildes."""
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    if columnas is None:
        columnas = []
        for f in filas:
            for k in f:
                if k not in columnas:
                    columnas.append(k)
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
        w.writeheader()
        for fila in filas:
            w.writerow({c: ("" if fila.get(c) is None else fila.get(c)) for c in columnas})


def num(x, defecto: float = 0.0) -> float:
    """Convierte a número aceptando coma decimal (0,75) y miles con punto (1.234,5)."""
    if x is None:
        return defecto
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(" ", "")
    if not s:
        return defecto
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return defecto


def es_verdadero(x) -> bool:
    return str(x).strip().lower() in {"1", "si", "sí", "true", "verdadero", "x", "s", "yes"}


def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


_PALABRA = re.compile(r"[a-z0-9ñ]+")


def tokens(texto: str) -> list[str]:
    """Minúsculas, sin tildes (conserva la ñ) y solo caracteres alfanuméricos."""
    t = texto.lower().replace("ñ", "\x00")
    t = sin_tildes(t).replace("\x00", "ñ")
    return _PALABRA.findall(t)


def ngramas(toks: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def sha256(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def ahora_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def dividir_oraciones(texto: str) -> list[str]:
    """División simple en oraciones que respeta las citas entre corchetes."""
    partes = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡«\"(])", texto.strip())
    return [p.strip() for p in partes if p.strip()]
