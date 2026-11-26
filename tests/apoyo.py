"""Utilidades compartidas por las pruebas."""
from __future__ import annotations

import csv
import os
import shutil
import tempfile
import unittest

from memoria.demo import ruta_datos_demo
from memoria.proyecto import Proyecto


class ConCarpeta(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="memoria_prueba_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ruta(self, *partes):
        return os.path.join(self.tmp, *partes)

    def proyecto_demo(self) -> Proyecto:
        destino = self.ruta("demo")
        shutil.copytree(ruta_datos_demo(), destino, ignore=shutil.ignore_patterns("__pycache__"))
        return Proyecto(destino)


def escribir(ruta, columnas, filas, delimitador=","):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=delimitador)
        w.writerow(columnas)
        w.writerows(filas)
