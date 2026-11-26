import os
import unittest

from memoria.util import ErrorDatos, dividir_oraciones, leer_csv, num, tokens

from apoyo import ConCarpeta, escribir


class PruebaCSV(ConCarpeta):
    def test_punto_y_coma_de_excel(self):
        ruta = self.ruta("a.csv")
        escribir(ruta, ["municipio", "hechos"], [["Villa Ceiba", "30"], ["Puerto Arenal", "18"]], ";")
        filas = leer_csv(ruta)
        self.assertEqual(filas[0]["municipio"], "Villa Ceiba")
        self.assertEqual(filas[1]["hechos"], "18")

    def test_tabulador(self):
        ruta = self.ruta("t.csv")
        escribir(ruta, ["a", "b"], [["1", "2"]], "\t")
        self.assertEqual(leer_csv(ruta), [{"a": "1", "b": "2"}])

    def test_bom_y_windows_1252(self):
        ruta = self.ruta("w.csv")
        with open(ruta, "wb") as f:
            f.write("municipio;nota\r\nSan Telmo del Río;año\r\n".encode("cp1252"))
        self.assertEqual(leer_csv(ruta)[0]["municipio"], "San Telmo del Río")
        ruta2 = self.ruta("b.csv")
        with open(ruta2, "wb") as f:
            f.write("﻿id,x\n1,2\n".encode("utf-8"))
        self.assertIn("id", leer_csv(ruta2)[0])

    def test_columnas_obligatorias(self):
        ruta = self.ruta("c.csv")
        escribir(ruta, ["a"], [["1"]])
        with self.assertRaises(ErrorDatos) as e:
            leer_csv(ruta, obligatorias=("a", "b"))
        self.assertIn("b", str(e.exception))

    def test_archivo_inexistente_y_filas_vacias(self):
        self.assertEqual(leer_csv(self.ruta("no.csv")), [])
        ruta = self.ruta("v.csv")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("a,b\n1,2\n,\n")
        self.assertEqual(len(leer_csv(ruta)), 1)


class PruebaNumeros(unittest.TestCase):
    def test_coma_decimal_y_miles(self):
        self.assertEqual(num("0,75"), 0.75)
        self.assertEqual(num("1.234,5"), 1234.5)
        self.assertEqual(num("1,234.5"), 1234.5)
        self.assertEqual(num(""), 0.0)
        self.assertEqual(num("abc", -1), -1)
        self.assertEqual(num(3), 3.0)


class PruebaTexto(unittest.TestCase):
    def test_tokens_conservan_enie_y_quitan_tildes(self):
        self.assertEqual(tokens("Año de la Masacre en San Telmo del Río"), ["año", "de", "la", "masacre", "en", "san", "telmo", "del", "rio"])

    def test_oraciones_con_citas(self):
        o = dividir_oraciones("Primera frase [DOC-1#0]. Segunda frase. ¿Tercera?")
        self.assertEqual(len(o), 3)
        self.assertTrue(o[0].endswith("[DOC-1#0]."))


if __name__ == "__main__":
    unittest.main()
