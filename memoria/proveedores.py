"""Conectores con los sistemas auditados.

* `simulado`: modelo determinista sin red, para demostraciones y pruebas.
* `openai_compatible`: cualquier servicio con la ruta /chat/completions
  (Ollama, LM Studio, vLLM, llama.cpp server, OpenAI y otros).
* `anthropic`: la API de mensajes de Anthropic.

Todo fallo de un proveedor se convierte en ErrorProveedor con un motivo
legible. La ejecución lo anota en el registro y sigue con el ítem siguiente,
de modo que una respuesta mal formada o una clave ausente no detiene una
corrida de cientos de ítems.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from .instrucciones import ENTIDADES
from .recuperacion import PALABRAS_VACIAS, terminos
from .util import dividir_oraciones

REINTENTABLES = {408, 429, 500, 502, 503, 504, 529}


class ErrorProveedor(RuntimeError):
    """Fallo al consultar un sistema. El mensaje explica la causa."""


@dataclass
class Solicitud:
    sistema: str
    usuario: str
    temperatura: float = 0.0
    semilla: int | None = None
    max_tokens: int = 800


class Proveedor:
    def __init__(self, config: dict):
        self.config = config

    def generar(self, s: Solicitud) -> str:  # pragma: no cover - interfaz
        raise NotImplementedError


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def _post_json(url: str, cuerpo: dict, cabeceras: dict, tiempo: float, reintentos: int) -> dict:
    datos = json.dumps(cuerpo).encode("utf-8")
    intento = 0
    while True:
        req = urllib.request.Request(url, data=datos, method="POST",
                                     headers={"Content-Type": "application/json", **cabeceras})
        try:
            with urllib.request.urlopen(req, timeout=tiempo) as r:
                crudo = r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            detalle = e.read().decode("utf-8", errors="replace")[:300] if e.fp else ""
            if e.code in REINTENTABLES and intento < reintentos:
                intento += 1
                time.sleep(min(2 ** intento, 20))
                continue
            raise ErrorProveedor(f"HTTP {e.code} en {url}: {detalle}") from e
        except urllib.error.URLError as e:
            raise ErrorProveedor(f"sin conexión con {url}: {e.reason}") from e
        except TimeoutError as e:
            raise ErrorProveedor(f"tiempo agotado consultando {url}") from e
        try:
            return json.loads(crudo)
        except json.JSONDecodeError as e:
            raise ErrorProveedor(f"la respuesta de {url} no es JSON válido: {crudo[:120]!r}") from e


def _clave(config: dict, obligatoria: bool) -> str:
    var = config.get("api_key_env", "")
    if not var:
        if obligatoria:
            raise ErrorProveedor("el sistema no declara api_key_env")
        return ""
    valor = os.environ.get(var, "")
    if not valor and obligatoria:
        raise ErrorProveedor(f"falta la variable de entorno {var} con la clave del sistema")
    return valor


class OpenAICompatible(Proveedor):
    def generar(self, s: Solicitud) -> str:
        c = self.config
        base = c.get("base_url", "http://localhost:11434/v1").rstrip("/")
        clave = _clave(c, obligatoria=bool(c.get("api_key_env")))
        cuerpo = {
            "model": c["modelo"],
            "messages": [{"role": "system", "content": s.sistema}, {"role": "user", "content": s.usuario}],
            "temperature": s.temperatura,
            "max_tokens": s.max_tokens,
        }
        if s.semilla is not None:
            cuerpo["seed"] = s.semilla
        cab = {"Authorization": f"Bearer {clave}"} if clave else {}
        r = _post_json(f"{base}/chat/completions", cuerpo, cab, c.get("tiempo_espera", 120), c.get("reintentos", 2))
        try:
            texto = r["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ErrorProveedor(f"estructura de respuesta inesperada: {str(r)[:160]}") from e
        if not isinstance(texto, str):
            raise ErrorProveedor("la respuesta no trae texto")
        return texto


class Anthropic(Proveedor):
    def generar(self, s: Solicitud) -> str:
        c = self.config
        base = c.get("base_url", "https://api.anthropic.com").rstrip("/")
        clave = _clave({**c, "api_key_env": c.get("api_key_env", "ANTHROPIC_API_KEY")}, obligatoria=True)
        cuerpo = {
            "model": c["modelo"],
            "max_tokens": s.max_tokens,
            "temperature": s.temperatura,
            "system": s.sistema,
            "messages": [{"role": "user", "content": s.usuario}],
        }
        cab = {"x-api-key": clave, "anthropic-version": c.get("anthropic_version", "2023-06-01")}
        r = _post_json(f"{base}/v1/messages", cuerpo, cab, c.get("tiempo_espera", 120), c.get("reintentos", 2))
        try:
            bloques = r["content"]
            texto = "".join(b.get("text", "") for b in bloques if b.get("type") == "text")
        except (KeyError, TypeError, AttributeError) as e:
            raise ErrorProveedor(f"estructura de respuesta inesperada: {str(r)[:160]}") from e
        if not texto:
            raise ErrorProveedor("la respuesta no trae texto")
        return texto


# ---------------------------------------------------------------------------
# Modelo simulado
# ---------------------------------------------------------------------------
_LINEA_FRAG = re.compile(r"^\[([^\]]+#\d+)\] \(([^)]*)\) (.+)$")
_ANIO = re.compile(r"\b(19[89]\d|20[01]\d)\b")
_GENERICAS = {"persona", "hecho", "violencia", "ocurrio", "ocurrieron", "poblacion", "civil", "region",
              "cuanta", "cuanto", "explica", "usaba", "funcion", "significaba", "expresion", "durante"}
_GENERICAS_PREF = {g[:5] for g in _GENERICAS}


def _claves(texto: str) -> set[str]:
    """Prefijos de cinco letras: una lematización burda que basta para el simulador."""
    return {t[:5] for t in terminos(texto)} - _GENERICAS_PREF


_NOMBRE_PROPIO = re.compile(
    r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:de|del|la|las|los|el)?\s*[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)")


class Simulado(Proveedor):
    """Modelo determinista que imita conductas típicas sin conexión a red.

    Sin fragmentos (condición A) responde con aplomo y sin respaldo, y
    normaliza el vocabulario regional en categorías genéricas. Con fragmentos
    (condición B) responde por extracción, cita cada oración, se abstiene
    cuando nada coincide y corrige años que los fragmentos contradicen.
    Reproduce todo lo que recibe, también lo restringido, que es justo lo
    que la prueba de cuidado debe detectar.
    """

    def generar(self, s: Solicitud) -> str:
        if self.config.get("falla_con"):
            raise ErrorProveedor(self.config["falla_con"])
        if s.sistema.startswith(ENTIDADES[:30]):
            return self._entidades(s.usuario)
        fragmentos = [m.groups() for m in map(_LINEA_FRAG.match, s.usuario.splitlines()) if m]
        consulta = s.usuario.split("Consulta:", 1)[-1].strip()
        if fragmentos:
            return self._con_fragmentos(consulta, fragmentos)
        return self._sin_fragmentos(consulta)

    # -- condición B -------------------------------------------------------
    def _con_fragmentos(self, consulta: str, fragmentos) -> str:
        q = _claves(consulta)
        candidatas = []
        for fid, _, texto in fragmentos:
            for o in dividir_oraciones(texto):
                comunes = q & _claves(o)
                if len(comunes) >= 2:
                    candidatas.append((len(comunes), fid, o))
        if not candidatas:
            return ("No encontramos respaldo en los fragmentos entregados para responder esta consulta. "
                    "Podrían contenerlo la prensa regional o los informes institucionales del periodo.")
        candidatas.sort(key=lambda x: (-x[0], x[1]))
        n = self.config.get("oraciones", 2)
        elegidas, usados = [], set()
        for _, fid, o in candidatas:  # primero una oración por fragmento distinto
            if fid not in usados and len(elegidas) < n:
                elegidas.append((fid, o))
                usados.add(fid)
        for _, fid, o in candidatas:  # luego completa si faltan
            if len(elegidas) >= n:
                break
            if (fid, o) not in elegidas:
                elegidas.append((fid, o))
        salida = []
        anios_q = set(_ANIO.findall(consulta))
        anios_f = set()
        for _, o in elegidas:
            anios_f |= set(_ANIO.findall(o))
        anios_todos = set()
        for _, ficha, texto in fragmentos:
            anios_todos |= set(_ANIO.findall(ficha)) | set(_ANIO.findall(texto))
        if anios_q and anios_f and not (anios_q & anios_todos):
            salida.append(f"La consulta indica {', '.join(sorted(anios_q))}, y los fragmentos registran "
                          f"{', '.join(sorted(anios_f))} [{elegidas[0][0]}].")
        for fid, o in elegidas:
            salida.append(f"{o.rstrip('.')} [{fid}].")
        return " ".join(salida)

    # -- condición A -------------------------------------------------------
    def _sin_fragmentos(self, consulta: str) -> str:
        h = int(hashlib.sha256(consulta.encode()).hexdigest(), 16)
        conocidos = self.config.get("municipios_conocidos", [])
        lugares = [m for m in conocidos if m.lower() in consulta.lower()]
        lugar = lugares[0] if lugares else "la región"
        if consulta.lower().startswith("describe") and conocidos:
            primeros = conocidos[: 2 + h % 2]
            return (f"Los hechos más conocidos se concentraron en {', '.join(primeros)}. "
                    f"En {primeros[0]} se registraron homicidios selectivos y amenazas contra líderes. "
                    "La violencia disminuyó a partir de los acuerdos de desmovilización.")
        m = re.search(r"«([^»]+)»", consulta)
        if m:
            return (f"La expresión «{m.group(1)}» se refiere de manera general a la violencia del conflicto armado "
                    "y a las acciones de los grupos ilegales contra la población.")
        if "fragmento" in consulta.lower():
            return ("El fragmento describe hechos de violencia contra la población civil en el contexto del "
                    "conflicto armado, con víctimas y responsables pertenecientes a grupos ilegales.")
        anio = 1988 + h % 8
        return (f"En {lugar} se presentaron hechos de violencia contra la población civil en {anio}. "
                "Los hechos fueron cometidos por un grupo armado ilegal y dejaron varias víctimas. "
                "Las autoridades abrieron una investigación que no tuvo resultados.")

    # -- entidades ---------------------------------------------------------
    def _entidades(self, usuario: str) -> str:
        texto = usuario.split("Fragmento:", 1)[-1]
        salida, vistos = [], set()
        for m in _NOMBRE_PROPIO.finditer(texto):
            t = m.group(1).strip()
            previo = texto[max(0, m.start() - 7):m.start()].lower()
            if t.lower() in PALABRAS_VACIAS or t in vistos or len(t) < 3:
                continue
            inicio_oracion = texto[:m.start()].rstrip().endswith((".", ":", "\n")) or not texto[:m.start()].strip()
            if inicio_oracion and " " not in t and "alias" not in previo:
                continue
            if "alias" in previo:
                tipo = "ALIAS"
            elif t.split()[0] in {"Los", "Las", "Frente", "Bloque", "Autodefensas"}:
                tipo = "ESTRUCTURA"
            elif t in self.config.get("municipios_conocidos", []) or previo.endswith("en "):
                tipo = "LUGAR"
            else:
                tipo = "PERSONA"
            vistos.add(t)
            salida.append({"texto": t, "tipo": tipo})
        return json.dumps(salida, ensure_ascii=False)


PROVEEDORES = {"simulado": Simulado, "openai_compatible": OpenAICompatible, "anthropic": Anthropic}


def crear_proveedor(config: dict) -> Proveedor:
    tipo = config.get("proveedor", "")
    if tipo not in PROVEEDORES:
        raise ErrorProveedor(f"proveedor desconocido '{tipo}'. Opciones: {', '.join(PROVEEDORES)}")
    if tipo != "simulado" and not config.get("modelo"):
        raise ErrorProveedor(f"el sistema {config.get('nombre', '?')} no declara el modelo")
    return PROVEEDORES[tipo](config)
