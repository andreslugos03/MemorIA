import json

from memoria.asistente import Asistente, ErrorCorreccion, RegistroCorrecciones
from memoria.asistente.asistente import SISTEMA_POR_DEFECTO
from memoria.proveedores import Proveedor

from apoyo import ConCarpeta


class ModeloFijo(Proveedor):
    """Devuelve un texto fijo para probar el post-proceso."""

    def generar(self, s):
        return self.config["texto"]


class PruebaRequisitos(ConCarpeta):
    def setUp(self):
        super().setUp()
        self.p = self.proyecto_demo()
        self.a = Asistente(self.p)

    def fijo(self, texto):
        a = Asistente(self.p)
        a.proveedor = ModeloFijo({"texto": texto})
        return a

    def test_1_cada_afirmacion_muestra_documento_tipo_y_fecha(self):
        r = self.a.responder("¿Qué estableció la sentencia de 2015 sobre las muertes de Los Naranjos?")
        verificadas = [x for x in r.afirmaciones if x.verificada]
        self.assertTrue(verificadas)
        for x in verificadas:
            for pr in x.procedencias:
                self.assertTrue(pr.documento and pr.tipo_fuente and pr.fecha)

    def test_2_lexico_entre_comillas_con_hablante_y_epoca(self):
        r = self.a.responder("¿Qué significaba «Los del Puente» en Puerto Arenal?")
        exp = {x.termino: x for x in r.expresiones}
        self.assertIn("Los del Puente", exp)
        self.assertTrue(exp["Los del Puente"].hablante and exp["Los del Puente"].epoca)
        self.assertTrue(any("«Los del Puente»" in x.texto for x in r.afirmaciones))
        self.assertNotIn("««", " ".join(x.texto for x in r.afirmaciones))

    def test_2_termino_estigmatizante_nunca_queda_sin_comillas(self):
        r = self.fijo("Los llamaban desechables en el puerto [DOC-001#0].").responder("masacre La Playita Puerto Arenal 1991")
        self.assertIn("«desechables»", r.afirmaciones[0].texto)

    def test_3_discrepancias_entre_fuentes(self):
        r = self.a.responder("¿Cuántas personas fueron asesinadas en el barrio La Playita de Puerto Arenal en 1991?")
        campos = {(d.hecho, d.campo) for d in r.discrepancias}
        self.assertIn(("H-01", "victimas"), campos)
        self.assertIn(("H-01", "fecha"), campos)
        v = next(d for d in r.discrepancias if d.campo == "victimas")
        self.assertEqual({x["valor"] for x in v.versiones}, {"4", "5"})

    def test_3_declara_cuando_no_sabe(self):
        r = self.a.responder("¿Qué ocurrió en Palmar Viejo en 1999?")  # solo hay fuente restringida
        self.assertTrue(r.abstencion)
        self.assertEqual(r.documentos, [])
        self.assertIn("No encontramos respaldo", r.motivo_abstencion)

    def test_4_documento_antes_que_sintesis(self):
        t = self.a.responder("¿Qué ocurrió en Villa Ceiba en 1988?").a_texto()
        self.assertLess(t.index("DOCUMENTOS"), t.index("SÍNTESIS"))

    def test_5_correcciones_con_fecha_autoria_y_cadena(self):
        reg = RegistroCorrecciones(self.p.ruta_correcciones)
        with self.assertRaises(ErrorCorreccion):
            reg.proponer("", "lexico", "Los del Puente", "lexico", "x")
        c = reg.proponer("Asociación del Mercado (ficticia)", "lexico", "Los del Puente", "lexico",
                         "vendedoras y vecinos del puerto", "Memoria del mercado", campo="hablante")
        self.assertTrue(c["fecha_utc"].endswith("Z"))
        self.assertEqual(c["hash_anterior"], "0" * 64)
        reg.resolver(c["id"], "aceptada", "Panel de validación")
        ok, _ = reg.verificar()
        self.assertTrue(ok)
        r = Asistente(self.p).responder("¿Qué significaba «Los del Puente» en Puerto Arenal?")
        e = next(x for x in r.expresiones if x.termino == "Los del Puente")
        self.assertEqual(e.hablante, "vendedoras y vecinos del puerto")
        self.assertEqual(e.corregida_por, [c["id"]])

    def test_5_alterar_el_registro_se_detecta(self):
        reg = RegistroCorrecciones(self.p.ruta_correcciones)
        reg.proponer("Colectivo A", "documento", "DOC-001", "hecho", "La fecha correcta es marzo")
        reg.proponer("Colectivo B", "documento", "DOC-002", "hecho", "Otra precisión")
        with open(reg.ruta, encoding="utf-8") as f:
            lineas = f.readlines()
        primera = json.loads(lineas[0])
        primera["texto_propuesto"] = "texto cambiado a escondidas"
        lineas[0] = json.dumps(primera, ensure_ascii=False) + "\n"
        with open(reg.ruta, "w", encoding="utf-8") as f:
            f.writelines(lineas)
        ok, problemas = reg.verificar()
        self.assertFalse(ok)
        self.assertTrue(any("alterado" in x for x in problemas))

    def test_5_nota_comunitaria_aceptada_acompana_el_documento(self):
        reg = RegistroCorrecciones(self.p.ruta_correcciones)
        c = reg.proponer("Familias de La Playita (ficticio)", "documento", "DOC-001", "hecho", "Las víctimas fueron cinco")
        r1 = self.a.responder("masacre La Playita Puerto Arenal")
        self.assertFalse(any(d.notas_comunitarias for d in r1.documentos))  # aún no aceptada
        reg.resolver(c["id"], "aceptada", "Panel")
        r2 = self.a.responder("masacre La Playita Puerto Arenal")
        doc1 = next(d for d in r2.documentos if d.procedencia.documento == "DOC-001")
        self.assertEqual(doc1.notas_comunitarias[0]["id"], c["id"])


class PruebaCuidado(ConCarpeta):
    def setUp(self):
        super().setUp()
        self.p = self.proyecto_demo()

    def fijo(self, texto, sistema=None):
        a = Asistente(self.p, sistema)
        a.proveedor = ModeloFijo({"texto": texto})
        return a

    def test_nombres_de_victimas_reservados_salvo_que_se_pidan(self):
        texto = "Entre las víctimas estaba Rosa Elvira Peña [DOC-001#0]."
        r = self.fijo(texto).responder("¿Qué ocurrió en La Playita de Puerto Arenal en 1991?")
        self.assertIn("[nombre reservado]", r.afirmaciones[0].texto)
        self.assertNotIn("Rosa Elvira", r.afirmaciones[0].texto)
        r2 = self.fijo(texto).responder("¿Cuáles son los nombres de las víctimas de La Playita en Puerto Arenal?")
        self.assertIn("Rosa Elvira Peña", r2.afirmaciones[0].texto)

    def test_cita_inventada_y_afirmacion_sin_cita(self):
        r = self.fijo("Hubo cuatro víctimas [DOC-999#0]. Además hubo un incendio.").responder("masacre La Playita Puerto Arenal")
        self.assertFalse(r.afirmaciones[0].verificada)
        self.assertTrue(any("no entregado" in x for x in r.afirmaciones[0].avisos))
        self.assertTrue(any("sin cita" in x for x in r.afirmaciones[1].avisos))

    def test_solo_fuentes_publicas_tambien_con_modelo_local(self):
        r = Asistente(self.p, {**SISTEMA_POR_DEFECTO, "local": True}).responder("vereda La Cumbre Palmar Viejo alias Tigrillo")
        self.assertTrue(all(d.procedencia.documento not in ("DOC-007", "DOC-008", "DOC-013") for d in r.documentos))

    def test_testimonio_sin_consentimiento_no_aparece(self):
        r = Asistente(self.p).responder("escuela de Cañaverales del Sur maestros 1995 Don Aurelio")
        self.assertNotIn("DOC-009", [d.procedencia.documento for d in r.documentos])

    def test_fallo_del_modelo_conserva_los_documentos(self):
        a = Asistente(self.p, {**SISTEMA_POR_DEFECTO, "falla_con": "servicio caído"})
        r = a.responder("masacre La Playita Puerto Arenal")
        self.assertTrue(r.documentos)
        self.assertTrue(r.abstencion)
        self.assertTrue(any("servicio caído" in x for x in r.avisos))
