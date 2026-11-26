"""Conciliación entre codificadores.

Compara las hojas de dos o más codificadores, calcula un alfa preliminar por
variable, lista los desacuerdos y prepara una hoja de consenso con los
acuerdos ya llenos y los desacuerdos en blanco, para que una tercera persona
del panel los resuelva en la sesión de conciliación.
"""
from __future__ import annotations

import os
from collections import defaultdict

from .cegamiento import HOJAS, VARIABLES_ALFA, clave_unidad, columnas_hoja, hojas_codificadas, ruta_hoja
from .metricas import alfa_krippendorff, fmt, lectura_alfa
from .proyecto import Proyecto
from .util import escribir_csv


def conciliar(p: Proyecto, hoja: str, sobrescribir: bool = False) -> dict:
    if hoja not in HOJAS:
        raise ValueError(f"Hoja desconocida {hoja}. Opciones: {', '.join(HOJAS)}")
    hojas = {c: f for c, f in hojas_codificadas(p, hoja).items() if c.lower() != "consenso"}
    if len(hojas) < 2:
        return {"hoja": hoja, "codificadores": list(hojas), "desacuerdos": [], "alfas": [],
                "aviso": "Se necesitan al menos dos codificadores para conciliar."}
    unidades = defaultdict(dict)  # unidad -> codificador -> fila
    for cod, filas in hojas.items():
        for f in filas:
            unidades[clave_unidad(hoja, f)][cod] = f
    variables = HOJAS[hoja]["variables"]
    desacuerdos, consenso = [], []
    for u, por_cod in unidades.items():
        base = dict(next(iter(por_cod.values())))
        base["codificador"] = "consenso"
        base["observaciones"] = ""
        for var in variables:
            valores = {c: str(f.get(var, "")).strip() for c, f in por_cod.items()}
            llenos = {v.upper() if var == "codigo" else v for v in valores.values() if v != ""}
            if len(llenos) == 1 and all(v != "" for v in valores.values()):
                base[var] = llenos.pop()
            else:
                base[var] = ""
                if any(v != "" for v in valores.values()):
                    desacuerdos.append({"unidad": " / ".join(u), "variable": var,
                                        **{f"valor_{c}": v for c, v in valores.items()}})
        consenso.append(base)
    alfas = []
    for var, nivel in VARIABLES_ALFA[hoja]:
        datos = defaultdict(list)
        for u, por_cod in unidades.items():
            for f in por_cod.values():
                v = str(f.get(var, "")).strip()
                if v:
                    datos[u].append(v.upper() if var == "codigo" else v)
        al = alfa_krippendorff(datos, nivel)
        alfas.append({"variable": var, "nivel": nivel, "alfa": fmt(al), "lectura": lectura_alfa(al)})
    ruta_cons = ruta_hoja(p, hoja, "consenso")
    escrito = False
    if sobrescribir or not os.path.exists(ruta_cons):
        escribir_csv(ruta_cons, consenso, columnas_hoja(hoja))
        escrito = True
    escribir_csv(os.path.join(p.dir_hojas, f"desacuerdos_{hoja}.csv"), desacuerdos)
    return {"hoja": hoja, "codificadores": list(hojas), "desacuerdos": desacuerdos, "alfas": alfas,
            "hoja_consenso": ruta_cons, "consenso_escrito": escrito}
