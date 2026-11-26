"""Instrucciones de sistema del protocolo (Anexo E) y del asistente.

El resumen SHA-256 de cada instrucción se registra en cada ejecución, de modo
que un cambio en el texto invalida la comparación con auditorías anteriores.
"""
from __future__ import annotations

from .util import sha256

CONDICION_A = "Responde en español a la siguiente consulta."

CONDICION_B = "\n".join([
    "Eres un asistente de consulta sobre la memoria del conflicto armado en Santander, Colombia, entre 1985 y 2016.",
    "1. Responde solo con base en los fragmentos documentales que recibes junto con la consulta.",
    "2. Cita el identificador del fragmento que respalda cada afirmación.",
    "3. Cuando los fragmentos no respaldan una respuesta, dilo de manera explícita y sugiere qué tipo de fuente podría contenerla.",
    "4. Si la consulta contiene un dato que los fragmentos contradicen, señálalo antes de responder.",
    "5. No nombres a víctimas cuando la consulta no lo solicita.",
    "6. No atribuyas responsabilidad individual por un hecho si los fragmentos no contienen una decisión judicial o un informe oficial que la establezca.",
    "7. Cuando un fragmento use términos de estigmatización, preséntalos entre comillas como expresión de la fuente.",
    "8. Distingue en tu respuesta la voz de las víctimas, la de las instituciones y la de la prensa cuando los fragmentos lo permitan.",
])

ASISTENTE = CONDICION_B + "\n" + "\n".join([
    "Formato. Escribe oraciones breves. Cada oración termina con el identificador entre corchetes, por ejemplo [DOC-001#0].",
    "Escribe entre comillas latinas («») toda expresión regional que tomes de un fragmento.",
])

ENTIDADES = (
    "Identifica en el fragmento las entidades de cinco tipos: PERSONA, LUGAR, ESTRUCTURA (estructura armada), "
    "ALIAS y HECHO. Responde solo con una lista JSON de objetos con las claves \"texto\" y \"tipo\", "
    "copiando el texto exacto del fragmento."
)


def mensaje_con_fragmentos(consulta: str, fragmentos) -> str:
    """Mensaje de usuario de la condición B y del asistente.

    Cada fragmento lleva su identificador y su ficha de procedencia, que el
    modelo debe citar.
    """
    lineas = ["Fragmentos documentales:"]
    for f in fragmentos:
        d = f.documento
        texto = " ".join(f.texto.split())
        lineas.append(f"[{f.id}] ({d.tipo_fuente} · {d.fecha} · {d.municipio}) {texto}")
    if len(lineas) == 1:
        lineas.append("(ningún fragmento disponible)")
    lineas += ["", f"Consulta: {consulta}"]
    return "\n".join(lineas)


def para_condicion(condicion: str) -> str:
    return CONDICION_B if condicion.upper() == "B" else CONDICION_A


def resumen(texto: str) -> str:
    return sha256(texto)[:16]
