import unittest

from memoria.compuertas import CompuertaContenido, es_local, niveles_permitidos
from memoria.corpus import Documento

RESTRINGIDO = ("Nos sacaron de la vereda La Cumbre el 3 de mayo de 1999 y los hombres del alias "
               "Tigrillo dijeron que volverían por los que hablaran con la fiscalía.")


def doc(i, nivel, texto):
    return Documento(i, "t", "testimonial", "2016", "X", nivel, texto, consentimiento_ia=True)


EXTERNO = {"nombre": "ext", "proveedor": "anthropic", "local": False}
LOCAL = {"nombre": "loc", "proveedor": "openai_compatible", "local": True, "base_url": "http://localhost:11434/v1"}


class PruebaLocalidad(unittest.TestCase):
    def test_local_exige_declaracion_y_direccion(self):
        self.assertTrue(es_local(LOCAL))
        self.assertTrue(es_local({**LOCAL, "base_url": "http://127.0.0.1:8080/v1"}))
        self.assertFalse(es_local({**LOCAL, "base_url": "https://api.ejemplo.com/v1"}))
        self.assertFalse(es_local({**LOCAL, "local": False}))
        self.assertFalse(es_local(EXTERNO))
        self.assertTrue(es_local({"proveedor": "simulado", "local": True}))

    def test_niveles(self):
        self.assertEqual(niveles_permitidos(EXTERNO), {"publica"})
        self.assertEqual(niveles_permitidos(LOCAL), {"publica", "restringida", "embargada"})
        # la interfaz pública nunca recupera fuentes no públicas, tampoco con un modelo local
        self.assertEqual(niveles_permitidos(LOCAL, "publico"), {"publica"})


class PruebaCompuertaContenido(unittest.TestCase):
    def setUp(self):
        self.c = CompuertaContenido([doc("R1", "restringida", RESTRINGIDO), doc("P1", "publica", "Texto público cualquiera sobre el puerto.")])

    def test_retiene_ocho_palabras_seguidas(self):
        d = self.c.revisar(EXTERNO, "Explica esto: nos sacaron de la vereda La Cumbre el 3 de mayo")
        self.assertFalse(d.permitido)
        self.assertEqual(d.documentos, ["R1"])
        self.assertIn("8 palabras", d.motivo)

    def test_siete_palabras_no_bastan(self):
        self.assertTrue(self.c.revisar(EXTERNO, "nos sacaron de la vereda La Cumbre").permitido)

    def test_ignora_mayusculas_tildes_y_puntuacion(self):
        d = self.c.revisar(EXTERNO, "LOS HOMBRES DEL ALIAS TIGRILLO, DIJERON QUE VOLVERÍAN... por")
        self.assertFalse(d.permitido)

    def test_texto_publico_no_se_retiene(self):
        self.assertTrue(self.c.revisar(EXTERNO, "Texto público cualquiera sobre el puerto y algo más largo").permitido)

    def test_item_marcado_restringido_se_retiene_sin_coincidencias(self):
        d = self.c.revisar(EXTERNO, "pregunta sin coincidencias", nivel_item="restringida")
        self.assertFalse(d.permitido)
        self.assertFalse(self.c.revisar(EXTERNO, "x", nivel_item="embargada").permitido)

    def test_sistema_local_puede_procesar(self):
        self.assertTrue(self.c.revisar(LOCAL, RESTRINGIDO, nivel_item="restringida").permitido)


if __name__ == "__main__":
    unittest.main()
