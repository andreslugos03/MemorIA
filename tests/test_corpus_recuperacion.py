import json
import os
import unittest

from memoria.corpus import Documento, buscar_termino, cargar_documentos, contiene_terminos, fragmentar, EntradaLexico
from memoria.recuperacion import IndiceBM25, raiz
from memoria.util import ErrorDatos

from apoyo import ConCarpeta


def jsonl(ruta, docs):
    with open(ruta, "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")


BASE = {"titulo": "t", "fecha": "1991", "municipio": "X", "texto": "Texto de prueba."}


class PruebaCorpus(ConCarpeta):
    def test_validaciones(self):
        r = self.ruta("c.jsonl")
        jsonl(r, [{**BASE, "id": "A", "tipo_fuente": "novela", "nivel_acceso": "publica"}])
        with self.assertRaises(ErrorDatos):
            cargar_documentos(r)
        jsonl(r, [{**BASE, "id": "A", "tipo_fuente": "prensa", "nivel_acceso": "secreta"}])
        with self.assertRaises(ErrorDatos):
            cargar_documentos(r)
        jsonl(r, [{**BASE, "id": "A", "tipo_fuente": "prensa", "nivel_acceso": "publica"}] * 2)
        with self.assertRaises(ErrorDatos):
            cargar_documentos(r)
        with open(r, "w", encoding="utf-8") as f:
            f.write("{no es json}\n")
        with self.assertRaises(ErrorDatos):
            cargar_documentos(r)

    def test_testimonio_sin_registro_de_consentimiento_queda_fuera_de_la_ia(self):
        r = self.ruta("c.jsonl")
        jsonl(r, [{**BASE, "id": "T", "tipo_fuente": "testimonial", "nivel_acceso": "publica"},
                  {**BASE, "id": "P", "tipo_fuente": "prensa", "nivel_acceso": "publica"},
                  {**BASE, "id": "T2", "tipo_fuente": "testimonial", "nivel_acceso": "pública", "consentimiento_ia": "sí"}])
        docs = {d.id: d for d in cargar_documentos(r)}
        self.assertFalse(docs["T"].consentimiento_ia)
        self.assertTrue(docs["P"].consentimiento_ia)
        self.assertTrue(docs["T2"].consentimiento_ia)
        self.assertEqual(docs["T2"].nivel_acceso, "publica")

    def test_corpus_en_csv(self):
        r = self.ruta("c.csv")
        with open(r, "w", encoding="utf-8") as f:
            f.write("id;titulo;tipo_fuente;fecha;municipio;nivel_acceso;texto\nD1;Uno;prensa;1990;X;publica;Hola mundo.\n")
        self.assertEqual(cargar_documentos(r)[0].id, "D1")

    def test_fragmentos_con_solapamiento(self):
        texto = " ".join(f"Oración número {i} con algunas palabras de relleno." for i in range(40))
        d = Documento("D", "t", "prensa", "1990", "X", "publica", texto)
        fr = fragmentar(d, tamano=50, solapamiento=10)
        self.assertGreater(len(fr), 3)
        self.assertEqual(fr[0].id, "D#0")
        ultima_del_primero = fr[0].texto.split(". ")[-1]
        self.assertIn(ultima_del_primero.rstrip("."), fr[1].texto)

    def test_buscar_termino_y_variantes(self):
        e = EntradaLexico("limpieza social", ["limpieza"], "", "", "", False)
        h = buscar_termino("La Limpieza Social y la limpieza del puerto", e)
        self.assertEqual([x[2] for x in h], ["Limpieza Social", "limpieza"])
        self.assertEqual(contiene_terminos("los del Puente llegaron", ["Los del Puente", "desechables"]), 1)


class PruebaBM25(unittest.TestCase):
    def setUp(self):
        docs = [
            Documento("A", "t", "prensa", "1991", "X", "publica", "La masacre de La Playita dejó cuatro víctimas en el puerto."),
            Documento("B", "t", "institucional", "2013", "X", "publica", "El informe describe la economía del río."),
            Documento("R", "t", "testimonial", "2016", "X", "restringida", "La masacre de La Playita según un testimonio reservado.", consentimiento_ia=True),
            Documento("N", "t", "testimonial", "2014", "X", "publica", "La masacre de La Playita contada sin consentimiento.", consentimiento_ia=False),
        ]
        self.idx = IndiceBM25([f for d in docs for f in fragmentar(d)])

    def test_ordena_por_relevancia_y_plural(self):
        r = self.idx.buscar("masacres de La Playita", niveles={"publica"})
        self.assertEqual(r[0][0].documento.id, "A")
        self.assertEqual(raiz("masacres"), "masacre")

    def test_filtra_nivel_y_consentimiento(self):
        ids = {f.documento.id for f, _ in self.idx.buscar("masacre Playita", k=10, niveles={"publica"})}
        self.assertEqual(ids, {"A"})
        ids = {f.documento.id for f, _ in self.idx.buscar("masacre Playita", k=10)}
        self.assertEqual(ids, {"A", "R"})  # sin filtro de nivel; el testimonio sin consentimiento nunca entra

    def test_sin_coincidencias(self):
        self.assertEqual(self.idx.buscar("astronomía"), [])


if __name__ == "__main__":
    unittest.main()
