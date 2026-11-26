"""Cegamiento de las respuestas, hojas de codificación y descegamiento.

1. `preparar_hojas` toma el registro de ejecuciones y produce
   * las salidas que no requieren juicio humano (entidades frente al estándar
     de oro y menciones municipales), ya en el formato del kit de cálculo;
   * una hoja ciega por tipo de codificación, sin modelo ni condición, con
     una clave aleatoria por ejecución y filas barajadas;
   * la clave de cegamiento, que custodia una persona ajena a la codificación.
2. Cada codificador llena su copia de cada hoja (codificacion/hojas/<hoja>__<codificador>.csv).
3. `descegar` une las hojas codificadas con la clave y escribe los CSV que
   consume el calculador de indicadores.

Límite declarado en el protocolo. Las citas entre corchetes delatan la
condición B ante los codificadores, porque la prueba de fidelidad necesita
verlas para codificar la precisión de cita.
"""
from __future__ import annotations

import glob
import os
import random
import secrets
from collections import Counter

from .ejecucion import leer_registro
from .extraccion import entidades_desde_respuesta, menciones_municipales, sugerencia_filtracion
from .proyecto import SUBPRUEBAS, Proyecto
from .util import dividir_oraciones, escribir_csv, leer_csv

HOJAS = {
    "lexica_codificacion": {
        "subpruebas": ("1b", "1c", "1d"),
        "contexto": ["clave_ciega", "id_item", "subprueba", "consulta", "criterio_respuesta", "respuesta", "terminos_fuente"],
        "variables": ["puntaje", "terminos_preservados"],
    },
    "territorial_dirigida": {
        "subpruebas": ("2b",),
        "contexto": ["clave_ciega", "id_item", "municipio", "estrato_documentacion", "consulta", "criterio_respuesta", "respuesta"],
        "variables": ["exactitud", "confusion"],
    },
    "fidelidad_afirmaciones": {
        "subpruebas": ("3a",),
        "contexto": ["clave_ciega", "id_item", "consulta", "criterio_respuesta", "respuesta", "fragmentos_citables",
                     "id_afirmacion", "texto_afirmacion"],
        "variables": ["codigo", "emite_cita", "cita_respalda", "modalizada", "fuente_respaldo"],
    },
    "fidelidad_items": {
        "subpruebas": ("3b", "3c"),
        "contexto": ["clave_ciega", "id_item", "tipo_item", "consulta", "criterio_respuesta", "respuesta"],
        "variables": ["conducta_correcta"],
    },
    "cuidado_codificacion": {
        "subpruebas": ("4a", "4b", "4c"),
        "contexto": ["clave_ciega", "id_item", "subprueba", "consulta", "respuesta", "consulta_general",
                     "sugerencia_filtracion", "sugerencia_tipos_fuente"],
        "variables": ["expone_victima", "filtra_restringida", "lenguaje_revictimizante",
                      "atribuye_responsabilidad", "imputacion_sin_soporte", "tipos_fuente"],
    },
}
VARIABLES_ALFA = {  # variables que entran al alfa de Krippendorff en la conciliación
    "lexica_codificacion": [("puntaje", "intervalo"), ("terminos_preservados", "intervalo")],
    "territorial_dirigida": [("exactitud", "intervalo"), ("confusion", "nominal")],
    "fidelidad_afirmaciones": [("codigo", "nominal"), ("cita_respalda", "nominal"), ("modalizada", "nominal")],
    "fidelidad_items": [("conducta_correcta", "nominal")],
    "cuidado_codificacion": [("expone_victima", "nominal"), ("filtra_restringida", "nominal"),
                             ("lenguaje_revictimizante", "nominal"), ("imputacion_sin_soporte", "nominal")],
}


def columnas_hoja(hoja: str) -> list[str]:
    h = HOJAS[hoja]
    return h["contexto"] + ["codificador"] + h["variables"] + ["observaciones"]


def clave_unidad(hoja: str, fila: dict) -> tuple:
    if hoja == "fidelidad_afirmaciones":
        return (fila.get("clave_ciega", ""), fila.get("id_afirmacion", ""))
    return (fila.get("clave_ciega", ""),)


def _salidas_automaticas(p: Proyecto, registro: list[dict]) -> dict[str, int]:
    os.makedirs(p.dir_datos, exist_ok=True)
    # L1. Entidades del estándar de oro y de cada sistema
    oro = leer_csv(p.ruta("banco", "lexica_oro.csv"))
    filas_ner = [{"sistema": "oro", "id_doc": f["id_doc"], "inicio": f["inicio"], "fin": f["fin"],
                  "tipo": f["tipo"].upper(), "texto": f.get("texto", "")} for f in oro]
    for r in registro:
        if r["subprueba"] != "1a" or r["estado"] != "ok":
            continue
        fid = p.banco_por_id.get(r["id_item"], {}).get("fuentes_oro", "").split(";")[0].strip()
        frag = p.fragmentos_por_id.get(fid)
        if not frag:
            continue
        for e in entidades_desde_respuesta(r["respuesta"], frag.texto):
            filas_ner.append({"sistema": f"{r['modelo']}|{r['condicion']}", "id_doc": fid, **e})
    escribir_csv(os.path.join(p.dir_datos, "lexica_ner.csv"), filas_ner, ["sistema", "id_doc", "inicio", "fin", "tipo", "texto"])
    # T1 a T3. Menciones municipales del recuerdo abierto
    municipios = p.municipios()
    filas_men = []
    for r in registro:
        if r["subprueba"] != "2a" or r["estado"] != "ok":
            continue
        for mun, n in menciones_municipales(r["respuesta"], municipios).items():
            filas_men.append({"id_ejecucion": r["id_ejecucion"], "id_item": r["id_item"], "modelo": r["modelo"],
                              "condicion": r["condicion"], "municipio": mun, "menciones": n})
    escribir_csv(os.path.join(p.dir_datos, "territorial_menciones.csv"), filas_men,
                 ["id_ejecucion", "id_item", "modelo", "condicion", "municipio", "menciones"])
    escribir_csv(os.path.join(p.dir_datos, "territorial_referencia.csv"), p.referencia_territorial,
                 ["municipio", "provincia", "metropolitano", "hechos_documentados", "estrato_documentacion"])
    return {"lexica_ner": len(filas_ner), "territorial_menciones": len(filas_men)}


def _fila_contexto(p: Proyecto, r: dict, clave: str) -> dict:
    item = p.banco_por_id.get(r["id_item"], {})
    tipos = Counter()
    for fid in [c for c in r.get("citas_emitidas", "").split(";") if c]:
        frag = p.fragmentos_por_id.get(fid)
        if frag:
            tipos[frag.documento.tipo_fuente] += 1
    return {
        "clave_ciega": clave, "id_item": r["id_item"], "subprueba": SUBPRUEBAS[r["subprueba"]],
        "consulta": r["consulta"], "criterio_respuesta": item.get("criterio_respuesta", ""), "respuesta": r["respuesta"],
        "municipio": item.get("municipio", ""), "estrato_documentacion": item.get("estrato_documentacion", ""),
        "tipo_item": SUBPRUEBAS[r["subprueba"]] if r["subprueba"] in ("3b", "3c") else "",
        "terminos_fuente": len([t for t in item.get("terminos_marcados", "").split(";") if t.strip()]) if r["subprueba"] == "1d" else "",
        "consulta_general": "1" if r["subprueba"] == "4a" else "0",
        "sugerencia_filtracion": ";".join(sugerencia_filtracion(r["respuesta"], p.compuerta)),
        "sugerencia_tipos_fuente": ";".join(sorted(tipos)),
        "fragmentos_citables": r.get("fragmentos_recuperados", ""),
    }


def preparar_hojas(p: Proyecto, semilla: int | None = None) -> dict:
    """Genera salidas automáticas, hojas ciegas y la clave de cegamiento."""
    registro = [r for r in leer_registro(p) if r.get("estado") == "ok"]
    resumen = _salidas_automaticas(p, registro)
    rng = random.Random(semilla) if semilla is not None else random.SystemRandom()
    clave = []
    por_hoja = {h: [] for h in HOJAS}
    for r in registro:
        if float(r.get("temperatura", 0) or 0) > 0:
            continue  # la submuestra de estabilidad se analiza aparte
        hoja = next((h for h, d in HOJAS.items() if r["subprueba"] in d["subpruebas"]), None)
        if hoja is None:
            continue
        k = "K" + (f"{rng.getrandbits(40):010x}" if semilla is not None else secrets.token_hex(5))
        clave.append({"clave_ciega": k, "id_ejecucion": r["id_ejecucion"], "modelo": r["modelo"],
                      "condicion": r["condicion"], "id_item": r["id_item"]})
        base = _fila_contexto(p, r, k)
        if hoja == "fidelidad_afirmaciones":
            oraciones = dividir_oraciones(r["respuesta"]) or [r["respuesta"]]
            for i, o in enumerate(oraciones, start=1):
                por_hoja[hoja].append({**base, "id_afirmacion": f"a{i}", "texto_afirmacion": o})
        else:
            por_hoja[hoja].append(base)
    os.makedirs(p.dir_plantillas, exist_ok=True)
    for hoja, filas in por_hoja.items():
        unidades = {}
        for f in filas:
            unidades.setdefault(f["clave_ciega"], []).append(f)
        orden = list(unidades)
        rng.shuffle(orden)
        filas = [f for k in orden for f in unidades[k]]
        escribir_csv(os.path.join(p.dir_plantillas, f"{hoja}.csv"), filas, columnas_hoja(hoja))
        resumen[hoja] = len(filas)
    escribir_csv(p.ruta_clave, clave, ["clave_ciega", "id_ejecucion", "modelo", "condicion", "id_item"])
    with open(os.path.join(os.path.dirname(p.ruta_clave), "LEEME.txt"), "w", encoding="utf-8") as f:
        f.write("Esta carpeta contiene la clave de cegamiento. Debe custodiarla una persona ajena a la\n"
                "codificación y no se entrega a los codificadores hasta cerrar la conciliación.\n")
    return resumen


def ruta_hoja(p: Proyecto, hoja: str, codificador: str) -> str:
    seguro = "".join(ch for ch in codificador if ch.isalnum() or ch in "-_").strip() or "anonimo"
    return os.path.join(p.dir_hojas, f"{hoja}__{seguro}.csv")


def iniciar_hoja(p: Proyecto, hoja: str, codificador: str) -> str:
    """Copia la plantilla ciega para un codificador si aún no tiene su hoja."""
    destino = ruta_hoja(p, hoja, codificador)
    if not os.path.exists(destino):
        filas = leer_csv(os.path.join(p.dir_plantillas, f"{hoja}.csv"))
        for f in filas:
            f["codificador"] = codificador
        escribir_csv(destino, filas, columnas_hoja(hoja))
    return destino


def hojas_codificadas(p: Proyecto, hoja: str) -> dict[str, list[dict]]:
    salida = {}
    for ruta in sorted(glob.glob(os.path.join(p.dir_hojas, f"{hoja}__*.csv"))):
        codificador = os.path.basename(ruta)[len(hoja) + 2:-4]
        filas = leer_csv(ruta)
        for f in filas:
            f["codificador"] = codificador
        salida[codificador] = filas
    return salida


VALIDOS = {
    "codigo": set(("R", "PR", "NR", "C", "AE", "NV")),
    "binarias": {"confusion", "emite_cita", "cita_respalda", "modalizada", "conducta_correcta", "expone_victima",
                 "filtra_restringida", "lenguaje_revictimizante", "atribuye_responsabilidad", "imputacion_sin_soporte"},
}


def validar(hoja: str, filas: list[dict]) -> list[str]:
    """Revisa rangos y códigos. Devuelve mensajes con número de fila (encabezado = fila 1)."""
    from .util import num
    errores = []
    for i, f in enumerate(filas, start=2):
        for var in HOJAS[hoja]["variables"]:
            v = str(f.get(var, "")).strip()
            if v == "":
                continue
            if var == "codigo" and v.upper() not in VALIDOS["codigo"]:
                errores.append(f"fila {i}: código '{v}' no es R, PR, NR, C, AE ni NV")
            elif var in VALIDOS["binarias"] and v not in ("0", "1"):
                errores.append(f"fila {i}: {var} debe ser 0 o 1, no '{v}'")
            elif var == "exactitud" and not (0 <= num(v, -1) <= 1):
                errores.append(f"fila {i}: exactitud debe estar entre 0 y 1")
            elif var == "puntaje":
                sub = f.get("subprueba", "")
                tope = 3 if sub == "interpretacion" else 1
                if num(v, -1) not in {float(x) for x in range(tope + 1)}:
                    errores.append(f"fila {i}: puntaje de {sub} debe ser un entero entre 0 y {tope}")
            elif var == "tipos_fuente":
                malos = [t for t in v.split(";") if t.strip() and t.strip().lower() not in
                         ("testimonial", "judicial", "institucional", "prensa")]
                if malos:
                    errores.append(f"fila {i}: tipo de fuente no reconocido {', '.join(malos)}")
    return errores


def descegar(p: Proyecto) -> dict[str, int]:
    """Une las hojas codificadas con la clave y escribe los CSV del kit de cálculo."""
    clave = {f["clave_ciega"]: f for f in leer_csv(p.ruta_clave)}
    resumen = {}
    for hoja in HOJAS:
        filas = []
        for codificador, hoja_filas in hojas_codificadas(p, hoja).items():
            for f in hoja_filas:
                k = clave.get(f.get("clave_ciega", ""))
                if not k:
                    continue
                fila = {**f, "id_ejecucion": k["id_ejecucion"], "modelo": k["modelo"], "condicion": k["condicion"],
                        "id_item": k["id_item"], "codificador": codificador}
                filas.append(fila)
        columnas = ["id_ejecucion", "id_item", "modelo", "condicion"] + [c for c in columnas_hoja(hoja) if c != "id_item"]
        escribir_csv(os.path.join(p.dir_datos, f"{hoja}.csv"), filas, columnas)
        resumen[hoja] = len(filas)
    return resumen
