import json
import os
from collections import Counter

from memoria.cegamiento import HOJAS, descegar, hojas_codificadas, iniciar_hoja, preparar_hojas, ruta_hoja, validar
from memoria.conciliacion import conciliar
from memoria.ejecucion import ejecutar, guardar_registro, leer_registro, planificar
from memoria.util import escribir_csv, leer_csv

from apoyo import ConCarpeta


class PruebaEjecucion(ConCarpeta):
    def setUp(self):
        super().setUp()
        self.p = self.proyecto_demo()

    def test_plan_incluye_repeticiones_del_recuerdo_abierto(self):
        tareas = planificar(self.p, self.p.sistemas[:1], ("A",))
        por_sub = Counter(t.item["subprueba"] for t in tareas)
        n_2a = sum(1 for i in self.p.banco if i["subprueba"] == "2a")
        self.assertEqual(por_sub["2a"], n_2a * 5)

    def test_submuestra_de_estabilidad(self):
        base = len(planificar(self.p, self.p.sistemas[:1], ("A",)))
        con = planificar(self.p, self.p.sistemas[:1], ("A",), estabilidad=True)
        self.assertGreater(len(con), base)
        self.assertTrue(any(t.temperatura == 0.7 for t in con))

    def test_compuertas_retienen_y_el_registro_queda_completo(self):
        filas = ejecutar(self.p)
        retenidas = {(f["modelo"], f["id_item"]) for f in filas if f["estado"] == "retenida"}
        # el sistema externo no recibe ítems restringidos ni el ítem mal marcado (segunda compuerta)
        self.assertIn(("simulado-externo", "C4B-01"), retenidas)
        self.assertIn(("simulado-externo", "C4B-02"), retenidas)
        self.assertIn(("simulado-externo", "L1C-03"), retenidas)
        self.assertFalse(any(m == "simulado-local" for m, _ in retenidas))
        detalle = next(f["detalle"] for f in filas if f["id_item"] == "L1C-03" and f["modelo"] == "simulado-externo")
        self.assertIn("DOC-007", detalle)
        reg = leer_registro(self.p)
        self.assertEqual(len(reg), len(filas))
        for campo in ("hash_prompt_sistema", "fecha_hora_utc", "version_modelo", "fragmentos_recuperados"):
            self.assertIn(campo, reg[0])

    def test_condicion_b_externa_solo_recupera_fuentes_publicas(self):
        filas = ejecutar(self.p, ["simulado-externo"], ("B",))
        publicos = {d.id for d in self.p.documentos if d.publico and d.consentimiento_ia}
        for f in filas:
            for fid in filter(None, f["fragmentos_recuperados"].split(";")):
                self.assertIn(fid.split("#")[0], publicos)

    def test_un_proveedor_que_falla_no_detiene_la_corrida(self):
        with open(self.p.ruta("sistemas.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["sistemas"].append({"nombre": "roto", "proveedor": "simulado", "local": True, "falla_con": "respuesta mal formada"})
        cfg["sistemas"].append({"nombre": "sin-modelo", "proveedor": "openai_compatible", "local": False})
        with open(self.p.ruta("sistemas.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        from memoria.proyecto import Proyecto
        p = Proyecto(self.p.raiz)
        filas = ejecutar(p, hilos=4)
        estados = Counter((f["modelo"], f["estado"]) for f in filas)
        self.assertGreater(estados[("simulado-local", "ok")], 0)
        self.assertGreater(estados[("roto", "error")], 0)
        self.assertEqual(estados[("roto", "ok")], 0)
        self.assertTrue(all("modelo" in f["detalle"] for f in filas if f["modelo"] == "sin-modelo" and f["estado"] == "error"))

    def test_reejecutar_reemplaza_y_no_duplica(self):
        f1 = ejecutar(self.p, ["simulado-local"], ("A",))
        ejecutar(self.p, ["simulado-local"], ("A",))
        self.assertEqual(len(leer_registro(self.p)), len(f1))
        guardar_registro(self.p, [{**f1[0], "respuesta": "otra"}])
        self.assertEqual(len(leer_registro(self.p)), len(f1))


class PruebaCegamiento(ConCarpeta):
    def setUp(self):
        super().setUp()
        self.p = self.proyecto_demo()
        ejecutar(self.p)
        self.resumen = preparar_hojas(self.p, semilla=3)

    def test_hojas_ciegas_no_revelan_sistema_ni_condicion(self):
        for hoja in HOJAS:
            filas = leer_csv(os.path.join(self.p.dir_plantillas, f"{hoja}.csv"))
            self.assertTrue(filas, hoja)
            for col in ("modelo", "condicion", "id_ejecucion", "proveedor"):
                self.assertNotIn(col, filas[0], f"{hoja} revela {col}")
            texto = json.dumps(filas, ensure_ascii=False)
            self.assertNotIn("simulado-externo", texto)

    def test_clave_unica_y_completa(self):
        clave = leer_csv(self.p.ruta_clave)
        self.assertEqual(len({c["clave_ciega"] for c in clave}), len(clave))
        self.assertTrue(os.path.exists(os.path.join(os.path.dirname(self.p.ruta_clave), "LEEME.txt")))

    def test_salidas_automaticas(self):
        ner = leer_csv(os.path.join(self.p.dir_datos, "lexica_ner.csv"))
        self.assertTrue(any(f["sistema"] == "oro" for f in ner))
        self.assertTrue(any(f["sistema"] == "simulado-local|A" for f in ner))
        men = leer_csv(os.path.join(self.p.dir_datos, "territorial_menciones.csv"))
        self.assertTrue(men)

    def test_sugerencia_de_filtracion_para_el_sistema_local(self):
        filas = leer_csv(os.path.join(self.p.dir_plantillas, "cuidado_codificacion.csv"))
        self.assertTrue(any("DOC-007" in f["sugerencia_filtracion"] for f in filas))

    def test_validacion(self):
        filas = [{"codigo": "X", "subprueba": "", "emite_cita": "2"}]
        errores = validar("fidelidad_afirmaciones", filas)
        self.assertEqual(len(errores), 2)
        self.assertEqual(validar("lexica_codificacion", [{"subprueba": "interpretacion", "puntaje": "4"}])[0][:6], "fila 2")
        self.assertFalse(validar("lexica_codificacion", [{"subprueba": "eufemismo", "puntaje": "1"}]))
        self.assertTrue(validar("territorial_dirigida", [{"exactitud": "1,5"}]))
        self.assertTrue(validar("cuidado_codificacion", [{"tipos_fuente": "prensa;novela"}]))

    def test_conciliacion_y_descegamiento(self):
        hoja = "fidelidad_items"
        for cod in ("ana", "beto"):
            ruta = iniciar_hoja(self.p, hoja, cod)
            filas = leer_csv(ruta)
            for i, f in enumerate(filas):
                f["conducta_correcta"] = "1" if (cod == "ana" or i > 0) else "0"
            escribir_csv(ruta, filas, list(filas[0]))
        r = conciliar(self.p, hoja)
        self.assertEqual(len(r["desacuerdos"]), 1)
        consenso = leer_csv(ruta_hoja(self.p, hoja, "consenso"))
        self.assertEqual(sum(1 for f in consenso if f["conducta_correcta"] == ""), 1)
        self.assertEqual(set(hojas_codificadas(self.p, hoja)), {"ana", "beto", "consenso"})
        # la conciliación no pisa un consenso ya trabajado salvo que se pida
        r2 = conciliar(self.p, hoja)
        self.assertFalse(r2["consenso_escrito"])
        descegar(self.p)
        datos = leer_csv(os.path.join(self.p.dir_datos, f"{hoja}.csv"))
        self.assertEqual({f["modelo"] for f in datos}, {"simulado-local", "simulado-externo"})
        self.assertTrue(all(f["condicion"] in ("A", "B") for f in datos))

    def test_conciliar_con_un_solo_codificador_avisa(self):
        iniciar_hoja(self.p, "cuidado_codificacion", "solo")
        r = conciliar(self.p, "cuidado_codificacion")
        self.assertIn("al menos dos", r["aviso"])
