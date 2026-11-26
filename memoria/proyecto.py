"""Proyecto de auditoría: carpeta con corpus, banco, sistemas, registros y resultados.

    proyecto/
      proyecto.json                     configuración general
      sistemas.json                     sistemas auditados
      corpus/documentos.jsonl           corpus con metadatos de acceso
      corpus/lexico.csv                 léxico regional validado
      banco/banco_items.csv             banco de ítems (Anexo C.1)
      banco/lexica_oro.csv              anotación de oro de entidades (subprueba 1a)
      banco/territorial_referencia.csv  distribución documentada por municipio
      registros/registro_ejecuciones.csv
      codificacion/plantillas/          hojas ciegas sin codificar
      codificacion/hojas/               hojas de cada codificador y de consenso
      codificacion/custodia/            clave de cegamiento (no entregar a codificadores)
      datos_metricas/                   CSV descegados en el formato del kit de cálculo
      resultados/                       métricas, fiabilidad, reporte y dictamen
      correcciones/correcciones.jsonl   registro de correcciones comunitarias
"""
from __future__ import annotations

import json
import os
from functools import cached_property

from .compuertas import CompuertaContenido
from .corpus import Documento, EntradaLexico, Fragmento, cargar_documentos, cargar_lexico, fragmentar
from .recuperacion import IndiceBM25
from .util import ErrorDatos, leer_csv

CONFIG_POR_DEFECTO = {
    "nombre": "Proyecto MemorIA",
    "corpus": "corpus/documentos.jsonl",
    "lexico": "corpus/lexico.csv",
    "tamano_fragmento": 120,
    "solapamiento": 30,
    "top_k": 4,
    "repeticiones_2a": 5,
    "fraccion_estabilidad": 0.2,
    "repeticiones_estabilidad": 5,
    "temperatura_estabilidad": 0.7,
    "puntaje_minimo_asistente": 1.0,
}

COLUMNAS_BANCO = ("id_item", "prueba", "subprueba", "consulta")
SUBPRUEBAS = {
    "1a": "reconocimiento", "1b": "interpretacion", "1c": "eufemismo", "1d": "preservacion",
    "2a": "recuerdo_abierto", "2b": "dirigida",
    "3a": "respondible", "3b": "no_respondible", "3c": "premisa_falsa",
    "4a": "consulta_general", "4b": "fuente_restringida", "4c": "responsabilidad",
}


class Proyecto:
    def __init__(self, raiz: str):
        self.raiz = os.path.abspath(raiz)
        ruta_cfg = os.path.join(self.raiz, "proyecto.json")
        cfg = {}
        if os.path.exists(ruta_cfg):
            with open(ruta_cfg, encoding="utf-8") as f:
                cfg = json.load(f)
        self.config = {**CONFIG_POR_DEFECTO, **cfg}

    # -- rutas -------------------------------------------------------------
    def ruta(self, *partes: str) -> str:
        return os.path.join(self.raiz, *partes)

    @property
    def ruta_registro(self) -> str:
        return self.ruta("registros", "registro_ejecuciones.csv")

    @property
    def ruta_clave(self) -> str:
        return self.ruta("codificacion", "custodia", "clave_cegamiento.csv")

    @property
    def dir_plantillas(self) -> str:
        return self.ruta("codificacion", "plantillas")

    @property
    def dir_hojas(self) -> str:
        return self.ruta("codificacion", "hojas")

    @property
    def dir_datos(self) -> str:
        return self.ruta("datos_metricas")

    @property
    def dir_resultados(self) -> str:
        return self.ruta("resultados")

    @property
    def ruta_correcciones(self) -> str:
        return self.ruta("correcciones", "correcciones.jsonl")

    # -- datos -------------------------------------------------------------
    @cached_property
    def documentos(self) -> list[Documento]:
        return cargar_documentos(self.ruta(self.config["corpus"]))

    @cached_property
    def documentos_por_id(self) -> dict[str, Documento]:
        return {d.id: d for d in self.documentos}

    @cached_property
    def fragmentos(self) -> list[Fragmento]:
        salida = []
        for d in self.documentos:
            salida += fragmentar(d, self.config["tamano_fragmento"], self.config["solapamiento"])
        return salida

    @cached_property
    def fragmentos_por_id(self) -> dict[str, Fragmento]:
        return {f.id: f for f in self.fragmentos}

    @cached_property
    def indice(self) -> IndiceBM25:
        return IndiceBM25(self.fragmentos)

    @cached_property
    def compuerta(self) -> CompuertaContenido:
        return CompuertaContenido(self.documentos)

    @cached_property
    def lexico(self) -> list[EntradaLexico]:
        ruta = self.ruta(self.config["lexico"])
        return cargar_lexico(ruta) if os.path.exists(ruta) else []

    @cached_property
    def banco(self) -> list[dict]:
        filas = leer_csv(self.ruta("banco", "banco_items.csv"), obligatorias=COLUMNAS_BANCO)
        vistos = set()
        for f in filas:
            if f["subprueba"] not in SUBPRUEBAS:
                raise ErrorDatos(f"banco_items.csv: subprueba '{f['subprueba']}' en {f['id_item']} no es válida")
            if f["id_item"] in vistos:
                raise ErrorDatos(f"banco_items.csv: id_item repetido {f['id_item']}")
            vistos.add(f["id_item"])
        return filas

    @cached_property
    def banco_por_id(self) -> dict[str, dict]:
        return {f["id_item"]: f for f in self.banco}

    @cached_property
    def referencia_territorial(self) -> list[dict]:
        return leer_csv(self.ruta("banco", "territorial_referencia.csv"))

    @cached_property
    def sistemas(self) -> list[dict]:
        ruta = self.ruta("sistemas.json")
        if not os.path.exists(ruta):
            return []
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
        sistemas = datos["sistemas"] if isinstance(datos, dict) else datos
        nombres = [s.get("nombre") for s in sistemas]
        if len(set(nombres)) != len(nombres) or not all(nombres):
            raise ErrorDatos("sistemas.json: cada sistema necesita un nombre único")
        return sistemas

    def sistema(self, nombre: str) -> dict:
        for s in self.sistemas:
            if s["nombre"] == nombre:
                return s
        raise ErrorDatos(f"No existe el sistema '{nombre}' en sistemas.json")

    def municipios(self) -> list[str]:
        return [f["municipio"] for f in self.referencia_territorial if f.get("municipio")]
