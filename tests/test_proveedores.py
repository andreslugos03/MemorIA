import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from memoria.proveedores import ErrorProveedor, Simulado, Solicitud, crear_proveedor
from memoria import instrucciones


class Servidor(BaseHTTPRequestHandler):
    """Servidor falso. El comportamiento depende del modelo pedido."""
    recibido = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        cuerpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Servidor.recibido.append((self.path, {k.lower(): v for k, v in self.headers.items()}, cuerpo))
        modo = cuerpo.get("model")
        if modo == "no-json":
            return self._enviar(200, b"<html>error de pasarela</html>")
        if modo == "http-500":
            return self._enviar(500, b'{"error":"interno"}')
        if modo == "sin-choices":
            return self._enviar(200, b'{"algo": 1}')
        if self.path.endswith("/v1/messages"):
            return self._enviar(200, json.dumps({"content": [{"type": "text", "text": "respuesta anthropic"}]}).encode())
        return self._enviar(200, json.dumps({"choices": [{"message": {"content": "respuesta openai"}}]}).encode())

    def _enviar(self, codigo, datos):
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(datos)


class PruebaHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"
        cls.srv = HTTPServer(("127.0.0.1", 0), Servidor)
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def oa(self, modelo, **extra):
        return crear_proveedor({"nombre": "x", "proveedor": "openai_compatible", "modelo": modelo,
                                "base_url": f"{self.url}/v1", "reintentos": 0, **extra})

    def test_openai_compatible(self):
        self.assertEqual(self.oa("m").generar(Solicitud("s", "u", 0, 42)), "respuesta openai")
        ruta, cab, cuerpo = Servidor.recibido[-1]
        self.assertEqual(ruta, "/v1/chat/completions")
        self.assertEqual(cuerpo["seed"], 42)
        self.assertEqual(cuerpo["messages"][0]["role"], "system")

    def test_respuesta_que_no_es_json(self):
        with self.assertRaises(ErrorProveedor) as e:
            self.oa("no-json").generar(Solicitud("s", "u"))
        self.assertIn("no es JSON", str(e.exception))

    def test_error_http_y_estructura_inesperada(self):
        with self.assertRaises(ErrorProveedor) as e:
            self.oa("http-500").generar(Solicitud("s", "u"))
        self.assertIn("HTTP 500", str(e.exception))
        with self.assertRaises(ErrorProveedor):
            self.oa("sin-choices").generar(Solicitud("s", "u"))

    def test_clave_ausente(self):
        os.environ.pop("CLAVE_INEXISTENTE_MEMORIA", None)
        with self.assertRaises(ErrorProveedor) as e:
            self.oa("m", api_key_env="CLAVE_INEXISTENTE_MEMORIA").generar(Solicitud("s", "u"))
        self.assertIn("CLAVE_INEXISTENTE_MEMORIA", str(e.exception))

    def test_clave_presente_viaja_en_cabecera(self):
        os.environ["CLAVE_PRUEBA_MEMORIA"] = "secreto"
        self.oa("m", api_key_env="CLAVE_PRUEBA_MEMORIA").generar(Solicitud("s", "u"))
        self.assertEqual(Servidor.recibido[-1][1].get("authorization"), "Bearer secreto")

    def test_anthropic(self):
        os.environ["CLAVE_ANTHROPIC_PRUEBA"] = "k"
        p = crear_proveedor({"nombre": "a", "proveedor": "anthropic", "modelo": "m", "base_url": self.url,
                             "api_key_env": "CLAVE_ANTHROPIC_PRUEBA", "reintentos": 0})
        self.assertEqual(p.generar(Solicitud("sistema", "u")), "respuesta anthropic")
        ruta, cab, cuerpo = Servidor.recibido[-1]
        self.assertEqual(ruta, "/v1/messages")
        self.assertEqual(cuerpo["system"], "sistema")
        self.assertEqual(cab.get("x-api-key"), "k")

    def test_sin_conexion(self):
        p = crear_proveedor({"nombre": "x", "proveedor": "openai_compatible", "modelo": "m",
                             "base_url": "http://127.0.0.1:9/v1", "reintentos": 0, "tiempo_espera": 2})
        with self.assertRaises(ErrorProveedor):
            p.generar(Solicitud("s", "u"))


class PruebaFabrica(unittest.TestCase):
    def test_proveedor_desconocido_o_sin_modelo(self):
        with self.assertRaises(ErrorProveedor):
            crear_proveedor({"proveedor": "otro"})
        with self.assertRaises(ErrorProveedor):
            crear_proveedor({"proveedor": "anthropic"})


class PruebaSimulado(unittest.TestCase):
    def setUp(self):
        self.s = Simulado({"municipios_conocidos": ["Villa Ceiba"]})

    def test_condicion_a_responde_sin_citas(self):
        r = self.s.generar(Solicitud(instrucciones.CONDICION_A, "¿Qué ocurrió en Villa Ceiba en 1990?"))
        self.assertNotIn("[", r)
        self.assertIn("Villa Ceiba", r)

    def test_condicion_b_cita_y_se_abstiene(self):
        msg = ("Fragmentos documentales:\n[D1#0] (prensa · 1991 · X) La masacre de La Playita dejó cuatro víctimas.\n\n"
               "Consulta: ¿Cuántas víctimas dejó la masacre de La Playita?")
        self.assertIn("[D1#0]", self.s.generar(Solicitud(instrucciones.CONDICION_B, msg)))
        msg2 = msg.replace("¿Cuántas víctimas dejó la masacre de La Playita?", "¿Quién ganó el campeonato de fútbol?")
        self.assertIn("No encontramos respaldo", self.s.generar(Solicitud(instrucciones.CONDICION_B, msg2)))

    def test_corrige_premisa_falsa(self):
        msg = ("Fragmentos documentales:\n[D4#0] (judicial · 2012 · X) La masacre de San Telmo ocurrió el 7 de junio de 1997.\n\n"
               "Consulta: ¿Por qué la masacre de San Telmo ocurrió en 1994?")
        self.assertIn("La consulta indica 1994", self.s.generar(Solicitud(instrucciones.CONDICION_B, msg)))

    def test_falla_configurada(self):
        with self.assertRaises(ErrorProveedor):
            Simulado({"falla_con": "caída simulada"}).generar(Solicitud("s", "u"))


if __name__ == "__main__":
    unittest.main()
