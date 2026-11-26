"""Aplicación del banco de ítems a cada sistema en las condiciones A y B.

Cada ejecución queda en registros/registro_ejecuciones.csv con los campos del
Anexo C.2, la respuesta completa sin edición y el estado (ok, error o
retenida). Un error de un proveedor no detiene la corrida.
"""
from __future__ import annotations

import random
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

from . import instrucciones
from .compuertas import es_local, niveles_permitidos
from .extraccion import citas
from .proveedores import ErrorProveedor, Solicitud, crear_proveedor
from .proyecto import Proyecto
from .util import ahora_utc, es_verdadero, escribir_csv, leer_csv, sha256

COLUMNAS_REGISTRO = [
    "id_ejecucion", "id_item", "prueba", "subprueba", "modelo", "version_modelo", "proveedor",
    "pesos_abiertos", "local", "condicion", "temperatura", "semilla", "repeticion", "fecha_hora_utc",
    "hash_prompt_sistema", "consulta", "respuesta", "fragmentos_recuperados", "citas_emitidas",
    "estado", "detalle", "ejecutor",
]


@dataclass
class Tarea:
    sistema: dict
    item: dict
    condicion: str
    repeticion: int
    temperatura: float


def id_ejecucion(sistema: str, item: str, condicion: str, repeticion: int, temperatura: float) -> str:
    return "E" + sha256(f"{sistema}|{item}|{condicion}|{repeticion}|{temperatura}")[:11]


def construir_mensajes(p: Proyecto, t: Tarea) -> tuple[str, str, list[str]]:
    """Devuelve (instrucción de sistema, mensaje de usuario, fragmentos entregados)."""
    item, consulta = t.item, t.item["consulta"]
    entregados = []
    contexto = ""
    if t.condicion == "B":
        niveles = niveles_permitidos(t.sistema, "auditoria")
        resultados = p.indice.buscar(consulta, k=int(p.config["top_k"]), niveles=niveles)
        entregados = [f for f, _ in resultados]
    if item["subprueba"] == "1a":
        frag = p.fragmentos_por_id.get(item.get("fuentes_oro", "").split(";")[0].strip())
        texto = frag.texto if frag else consulta
        if entregados:
            contexto = instrucciones.mensaje_con_fragmentos("(contexto)", entregados) + "\n\n"
        return instrucciones.ENTIDADES, f"{contexto}Fragmento: {texto}", [f.id for f in entregados]
    if t.condicion == "B":
        return instrucciones.CONDICION_B, instrucciones.mensaje_con_fragmentos(consulta, entregados), [f.id for f in entregados]
    return instrucciones.CONDICION_A, consulta, []


def planificar(p: Proyecto, sistemas: list[dict], condiciones=("A", "B"), estabilidad: bool = False,
               incluir_no_validados: bool = False) -> list[Tarea]:
    tareas = []
    items = [i for i in p.banco if incluir_no_validados or es_verdadero(i.get("validado_panel", "1"))]
    rng = random.Random(20260927)
    muestra = set()
    if estabilidad:
        candidatos = [i["id_item"] for i in items if i["subprueba"] != "2a"]
        n = max(1, round(len(candidatos) * float(p.config["fraccion_estabilidad"])))
        muestra = set(rng.sample(candidatos, min(n, len(candidatos))))
    for s in sistemas:
        temp = float(s.get("temperatura", 0))
        for item in items:
            for c in condiciones:
                reps = int(p.config["repeticiones_2a"]) if item["subprueba"] == "2a" else 1
                for r in range(1, reps + 1):
                    tareas.append(Tarea(s, item, c, r, temp))
                if item["id_item"] in muestra:
                    for r in range(1, int(p.config["repeticiones_estabilidad"]) + 1):
                        tareas.append(Tarea(s, item, c, r, float(p.config["temperatura_estabilidad"])))
    return tareas


def ejecutar_tarea(p: Proyecto, t: Tarea, proveedor, ejecutor: str = "") -> dict:
    s, item = t.sistema, t.item
    sistema_txt, usuario, entregados = construir_mensajes(p, t)
    fila = {
        "id_ejecucion": id_ejecucion(s["nombre"], item["id_item"], t.condicion, t.repeticion, t.temperatura),
        "id_item": item["id_item"], "prueba": item.get("prueba", ""), "subprueba": item["subprueba"],
        "modelo": s["nombre"], "version_modelo": s.get("version_modelo", s.get("modelo", "")),
        "proveedor": s.get("proveedor", ""), "pesos_abiertos": int(bool(s.get("pesos_abiertos", False))),
        "local": int(es_local(s)), "condicion": t.condicion, "temperatura": t.temperatura,
        "semilla": s.get("semilla", ""), "repeticion": t.repeticion, "fecha_hora_utc": ahora_utc(),
        "hash_prompt_sistema": instrucciones.resumen(sistema_txt), "consulta": item["consulta"],
        "respuesta": "", "fragmentos_recuperados": ";".join(entregados), "citas_emitidas": "",
        "estado": "ok", "detalle": "", "ejecutor": ejecutor,
    }
    decision = p.compuerta.revisar(s, sistema_txt + "\n" + usuario, item.get("nivel_acceso_fuentes", "publica"))
    if not decision.permitido:
        fila.update(estado="retenida", detalle=f"compuerta ética: {decision.motivo}")
        return fila
    if proveedor is None:
        fila.update(estado="error", detalle="el proveedor no pudo inicializarse")
        return fila
    try:
        semilla = s.get("semilla")
        respuesta = proveedor.generar(Solicitud(sistema_txt, usuario, t.temperatura,
                                                int(semilla) if semilla not in (None, "") else None,
                                                int(s.get("max_tokens", 800))))
    except ErrorProveedor as e:
        fila.update(estado="error", detalle=str(e))
        return fila
    except Exception as e:  # noqa: BLE001 - ningún fallo inesperado detiene la corrida
        fila.update(estado="error", detalle=f"{type(e).__name__}: {e}")
        return fila
    fila["respuesta"] = respuesta
    fila["citas_emitidas"] = ";".join(citas(respuesta))
    return fila


def ejecutar(p: Proyecto, nombres_sistemas: list[str] | None = None, condiciones=("A", "B"),
             estabilidad: bool = False, hilos: int = 1, ejecutor: str = "",
             progreso: Callable[[int, int], None] | None = None) -> list[dict]:
    sistemas = [p.sistema(n) for n in nombres_sistemas] if nombres_sistemas else p.sistemas
    tareas = planificar(p, sistemas, condiciones, estabilidad)
    proveedores = {}
    errores_init = {}
    for s in sistemas:
        try:
            proveedores[s["nombre"]] = crear_proveedor(s)
        except ErrorProveedor as e:
            proveedores[s["nombre"]] = None
            errores_init[s["nombre"]] = str(e)
    hechas, total, cerrojo = [0], len(tareas), threading.Lock()

    def correr(t: Tarea) -> dict:
        fila = ejecutar_tarea(p, t, proveedores[t.sistema["nombre"]], ejecutor)
        if fila["estado"] == "error" and t.sistema["nombre"] in errores_init:
            fila["detalle"] = errores_init[t.sistema["nombre"]]
        with cerrojo:
            hechas[0] += 1
            if progreso:
                progreso(hechas[0], total)
        return fila

    if hilos > 1:
        with ThreadPoolExecutor(max_workers=hilos) as ex:
            filas = list(ex.map(correr, tareas))
    else:
        filas = [correr(t) for t in tareas]
    guardar_registro(p, filas)
    return filas


def guardar_registro(p: Proyecto, filas_nuevas: list[dict]) -> None:
    """Combina con el registro existente. Una ejecución repetida reemplaza a la anterior."""
    previas = {f["id_ejecucion"]: f for f in leer_csv(p.ruta_registro)}
    for f in filas_nuevas:
        previas[f["id_ejecucion"]] = f
    escribir_csv(p.ruta_registro, list(previas.values()), COLUMNAS_REGISTRO)


def leer_registro(p: Proyecto) -> list[dict]:
    return leer_csv(p.ruta_registro)
