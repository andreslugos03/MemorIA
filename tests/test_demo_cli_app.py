import contextlib
import io
import json
import os
import unittest

from memoria import cli
from memoria.demo import demo_completa

from apoyo import ConCarpeta


class PruebaDemo(ConCarpeta):
    def test_demo_de_punta_a_punta(self):
        calc = demo_completa(self.ruta("d"))
        dic = {k: v["dictamen"] for k, v in calc["dictamenes"].items()}
        self.assertEqual(dic[("simulado-local", "A")], "DIAGNÓSTICO")
        self.assertEqual(dic[("simulado-externo", "A")], "DIAGNÓSTICO")
        # el sistema local con acceso a fuentes restringidas las filtra: fallo crítico
        local_b = calc["dictamenes"][("simulado-local", "B")]
        self.assertEqual(local_b["dictamen"], "NO HABILITADO")
        self.assertIn("C2_TFR_filtracion_restringida", local_b["fallos_criticos"])
        # el corpus corrige la alucinación de la condición A
        r = calc["resultados"]
        self.assertLess(r[("simulado-externo", "B")]["F2_TA_alucinacion"], r[("simulado-externo", "A")]["F2_TA_alucinacion"])
        for f in ("metricas.csv", "fiabilidad.csv", "efecto_correctivo.csv", "dictamen.json", "reporte_auditoria.md"):
            self.assertTrue(os.path.exists(self.ruta("d", "resultados", f)))

    def test_demo_reproducible(self):
        a = demo_completa(self.ruta("a"))
        b = demo_completa(self.ruta("b"))
        self.assertEqual([x["valor"] for x in a["filas"]], [x["valor"] for x in b["filas"]])

    def test_no_sobrescribe_sin_permiso(self):
        demo_completa(self.ruta("c"))
        with self.assertRaises(FileExistsError):
            demo_completa(self.ruta("c"))


def correr(*args):
    salida = io.StringIO()
    codigo = 0
    with contextlib.redirect_stdout(salida):
        try:
            cli.main(list(args))
        except SystemExit as e:
            codigo = e.code if isinstance(e.code, int) else 1
    return codigo, salida.getvalue()


class PruebaCLI(ConCarpeta):
    def test_flujo_completo_por_ordenes(self):
        d = self.ruta("p")
        self.assertEqual(correr("demo", d, "--solo-instalar")[0], 0)
        c, out = correr("ejecutar", d, "--sistemas", "simulado-externo")
        self.assertIn("retenida", out)
        self.assertEqual(correr("cegar", d, "--semilla", "1")[0], 0)
        c, out = correr("hoja", d, "todas", "cod1")
        self.assertEqual(c, 0)
        self.assertIn("cuidado_codificacion__cod1.csv", out)
        self.assertEqual(correr("validar", d)[0], 0)
        c, out = correr("conciliar", d)
        self.assertIn("al menos dos", out)
        self.assertEqual(correr("descegar", d)[0], 0)
        c, out = correr("dictamen", d)
        self.assertEqual(c, 0)

    def test_consultar_y_corregir(self):
        d = self.ruta("q")
        correr("demo", d, "--solo-instalar")
        c, out = correr("consultar", d, "¿Qué ocurrió en Villa Ceiba en 1988?")
        self.assertIn("DOCUMENTOS", out)
        c, out = correr("consultar", d, "¿Qué ocurrió en Villa Ceiba en 1988?", "--json")
        self.assertIn("documentos", json.loads(out))
        c, out = correr("corregir", d, "proponer", "--autoria", "Colectivo X", "--objeto-tipo", "documento",
                        "--objeto-id", "DOC-010", "--categoria", "hecho", "--texto", "precisión")
        self.assertIn("CORR-0001", out)
        self.assertEqual(correr("corregir", d, "resolver", "CORR-0001", "--estado", "aceptada", "--autoria", "Panel")[0], 0)
        c, out = correr("corregir", d, "listar")
        self.assertIn("aceptada", out)
        c, out = correr("corregir", d, "verificar")
        self.assertEqual(c, 0)
        self.assertIn("íntegro", out)
        self.assertNotEqual(correr("corregir", d, "resolver", "CORR-9999", "--estado", "aceptada", "--autoria", "P")[0], 0)

    def test_version(self):
        c, out = correr("--version")
        self.assertIn("protocolo v1.0", out)


try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # pragma: no cover
    AppTest = None


def tipos_de_elementos(nodo, acumulado=None):
    """Tipos de todos los elementos renderizados, para detectar salidas «mágicas» de Streamlit."""
    acumulado = [] if acumulado is None else acumulado
    hijos = getattr(nodo, "children", None) or {}
    for hijo in (hijos.values() if isinstance(hijos, dict) else hijos):
        acumulado.append(str(getattr(hijo, "type", type(hijo).__name__)))
        tipos_de_elementos(hijo, acumulado)
    return acumulado


@unittest.skipIf(AppTest is None, "streamlit no está instalado")
class PruebaApp(ConCarpeta):
    def test_todas_las_paginas_se_renderizan(self):
        d = self.ruta("app")
        demo_completa(d)
        os.environ["MEMORIA_PROYECTO"] = d
        try:
            ruta_app = os.path.join(os.path.dirname(cli.__file__), "app", "app.py")
            at = AppTest.from_file(ruta_app, default_timeout=120).run()
            self.assertFalse(at.exception)
            for pagina in ("Inicio", "Asistente", "Correcciones comunitarias", "Corpus y léxico", "Auditoría · ejecutar",
                           "Auditoría · codificar", "Auditoría · conciliar", "Dictamen"):
                at.sidebar.radio[0].set_value(pagina).run()
                self.assertFalse(at.exception, f"{pagina}: {list(at.exception)}")
                tipos = tipos_de_elementos(at._tree)
                self.assertNotIn("json", tipos, f"{pagina}: Streamlit imprimió una expresión suelta")
                self.assertFalse([t for t in tipos if "help" in t or "doc" in t], pagina)
            at.sidebar.radio[0].set_value("Asistente").run()
            at.text_input(key="consulta").set_value("¿Qué ocurrió en Puerto Arenal en 1991?").run()
            self.assertFalse(at.exception)
            self.assertIn("Documentos", [s.value for s in at.subheader])
        finally:
            os.environ.pop("MEMORIA_PROYECTO", None)

    def test_tema_y_estilo(self):
        from memoria.app import estilo
        ruta = os.path.join(os.path.dirname(cli.__file__), "app", "tema_apple.toml")
        self.assertTrue(os.path.exists(ruta))
        for tema in ("light", "dark"):
            css = estilo.css(tema)
            self.assertEqual(css.count("{"), css.count("}"), f"llaves desbalanceadas en el estilo {tema}")
            self.assertNotIn("}}", css)
            for i in range(1, len(estilo.NAVEGACION) + 1):
                self.assertIn(f"> div:nth-child({i}) label::before", css)
        self.assertIn("&lt;b&gt;", estilo.pastilla("<b>"))
        try:
            import tomllib
        except ImportError:  # Python 3.10
            return
        with open(ruta, "rb") as f:
            tema = tomllib.load(f)["theme"]
        self.assertEqual(tema["light"]["primaryColor"], "#007AFF")
        self.assertEqual(tema["dark"]["primaryColor"], "#0A84FF")
