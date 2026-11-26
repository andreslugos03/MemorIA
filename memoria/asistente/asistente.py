"""Asistente de consulta sobre el corpus (capítulo 8 de la tesis).

Traduce las tres propiedades del archivo (polifonía, temporalidad y autoría)
en cinco requisitos de comportamiento.

1. Cada afirmación muestra el documento del que procede, su tipo de fuente y su fecha.
2. Las expresiones del léxico regional aparecen entre comillas, con su hablante y su época.
3. El asistente señala las discrepancias entre fuentes y declara cuándo no sabe.
4. La interfaz sitúa el documento en primer plano y la síntesis en segundo.
5. Las comunidades pueden proponer correcciones, documentadas con fecha y autoría colectiva.

Reglas de cuidado que el asistente aplica además de la instrucción de sistema.
La interfaz pública recupera solo fuentes públicas, también cuando el modelo corre en
un computador local. Los testimonios sin consentimiento para procesamiento con
IA nunca entran. Los nombres de víctimas se reservan en la síntesis cuando la
consulta no los pide. Una afirmación cuya cita no corresponde a un fragmento
entregado queda marcada como no verificable.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .. import instrucciones
from ..compuertas import niveles_permitidos
from ..corpus import EntradaLexico, Fragmento, buscar_termino
from ..extraccion import citas
from ..proveedores import ErrorProveedor, Solicitud, crear_proveedor
from ..proyecto import Proyecto
from ..util import ahora_utc, dividir_oraciones
from .correcciones import RegistroCorrecciones

SISTEMA_POR_DEFECTO = {"nombre": "simulado-asistente", "proveedor": "simulado", "local": True,
                       "version_modelo": "simulado-0.4", "oraciones": 3}
_PIDE_NOMBRES = re.compile(
    r"\b(nombres?|c[oó]mo se llamaba[n]?|qui[eé]n(es)? (era|eran|fue|fueron) (la |las |los )?v[ií]ctimas?)\b",
    re.IGNORECASE)
_FRASES_ABSTENCION = ("no encontramos respaldo", "no hay registro", "no encontré", "no tenemos respaldo")
SUGERENCIA_FUENTES = ("la prensa regional del periodo, los informes de memoria histórica, las sentencias "
                      "de Justicia y Paz o los archivos de las organizaciones de víctimas")


@dataclass
class Procedencia:
    fragmento: str
    documento: str
    titulo: str
    tipo_fuente: str
    fecha: str
    municipio: str
    autoria: str


@dataclass
class Afirmacion:
    texto: str
    citas: list[str]
    procedencias: list[Procedencia]
    verificada: bool
    avisos: list[str] = field(default_factory=list)


@dataclass
class Expresion:
    termino: str
    formas: list[str]
    hablante: str
    epoca: str
    categoria: str
    estigmatizante: bool
    nota: str
    fragmentos: list[str]
    corregida_por: list[str] = field(default_factory=list)


@dataclass
class Discrepancia:
    hecho: str
    campo: str
    versiones: list[dict]


@dataclass
class DocumentoMostrado:
    procedencia: Procedencia
    texto: str
    puntaje: float
    notas_comunitarias: list[dict] = field(default_factory=list)


@dataclass
class Respuesta:
    consulta: str
    sistema: str
    fecha_utc: str
    documentos: list[DocumentoMostrado]
    afirmaciones: list[Afirmacion]
    expresiones: list[Expresion]
    discrepancias: list[Discrepancia]
    abstencion: bool
    motivo_abstencion: str = ""
    avisos: list[str] = field(default_factory=list)
    texto_modelo: str = ""

    def como_dict(self) -> dict:
        return asdict(self)

    def a_texto(self) -> str:
        """Representación de consola con el documento en primer plano."""
        L = [f"Consulta: {self.consulta}", ""]
        L.append("DOCUMENTOS")
        if not self.documentos:
            L.append("  Ningún documento público responde a esta consulta.")
        for i, d in enumerate(self.documentos, start=1):
            p = d.procedencia
            L.append(f"  [{i}] {p.titulo}")
            L.append(f"      {p.tipo_fuente} · {p.fecha} · {p.municipio} · {p.autoria} · {p.fragmento}")
            L.append(f"      {d.texto}")
            for n in d.notas_comunitarias:
                L.append(f"      Nota comunitaria {n['id']} ({n['autoria_colectiva']}, {n['fecha_utc'][:10]}): {n['texto_propuesto']}")
        if self.discrepancias:
            L += ["", "LAS FUENTES DISCREPAN"]
            for d in self.discrepancias:
                versiones = "; ".join(f"{v['valor']} según {v['tipo_fuente']} de {v['fecha']} ({v['documento']})"
                                      for v in d.versiones)
                L.append(f"  {d.hecho} · {d.campo}: {versiones}")
        if self.expresiones:
            L += ["", "EXPRESIONES DEL LÉXICO REGIONAL"]
            for e in self.expresiones:
                marca = " · término estigmatizante" if e.estigmatizante else ""
                L.append(f"  «{e.termino}» · usado por {e.hablante} · {e.epoca}{marca}")
                if e.nota:
                    L.append(f"      {e.nota}")
        L += ["", "SÍNTESIS (lectura secundaria, verifica en los documentos)"]
        if self.abstencion:
            L.append(f"  {self.motivo_abstencion}")
        for a in self.afirmaciones:
            fuentes = "; ".join(f"{p.tipo_fuente}, {p.fecha}, {p.documento}" for p in a.procedencias)
            L.append(f"  - {a.texto}" + (f"  ({fuentes})" if fuentes else "  (sin cita verificable)"))
        for av in self.avisos:
            L.append(f"  Aviso: {av}")
        return "\n".join(L)


def _procedencia(f: Fragmento) -> Procedencia:
    d = f.documento
    return Procedencia(f.id, d.id, d.titulo, d.tipo_fuente, d.fecha, d.municipio, d.autoria)


def _compatibles(a: str, b: str) -> bool:
    a, b = str(a).strip().lower(), str(b).strip().lower()
    return a == b or a.startswith(b) or b.startswith(a)


class Asistente:
    def __init__(self, proyecto: Proyecto, sistema: dict | None = None):
        self.p = proyecto
        self.sistema = sistema or SISTEMA_POR_DEFECTO
        self.proveedor = crear_proveedor(self.sistema)
        self.correcciones = RegistroCorrecciones(proyecto.ruta_correcciones)

    # -- léxico con correcciones aceptadas ----------------------------------
    def lexico_vigente(self) -> list[tuple[EntradaLexico, list[str]]]:
        aceptadas = [c for c in self.correcciones.aceptadas() if c["objeto"]["tipo"] == "lexico"]
        salida = []
        for e in self.p.lexico:
            e2 = EntradaLexico(**{**e.__dict__})
            ids = []
            for c in aceptadas:
                if c["objeto"]["id"].lower() == e.termino.lower() and c.get("campo") in ("hablante", "epoca", "nota", "categoria"):
                    setattr(e2, c["campo"], c["texto_propuesto"])
                    ids.append(c["id"])
            salida.append((e2, ids))
        return salida

    # -- requisito 3 ---------------------------------------------------------
    def discrepancias(self, fragmentos: list[Fragmento]) -> list[Discrepancia]:
        hechos = {h["id"] for f in fragmentos for h in f.documento.hechos if h.get("id")}
        salida = []
        for hid in sorted(hechos):
            versiones = []
            for d in self.p.documentos:
                if not (d.publico and d.consentimiento_ia):
                    continue
                for h in d.hechos:
                    if h.get("id") == hid:
                        versiones.append((d, h))
            for campo in ("fecha", "lugar", "victimas", "responsable"):
                vals = [(str(h[campo]), d) for d, h in versiones if str(h.get(campo, "")).strip()]
                conflicto = any(not _compatibles(a, b) for (a, _), (b, _) in
                                ((x, y) for i, x in enumerate(vals) for y in vals[i + 1:]))
                if conflicto:
                    salida.append(Discrepancia(hid, campo, [
                        {"valor": v, "documento": d.id, "tipo_fuente": d.tipo_fuente, "fecha": d.fecha, "titulo": d.titulo}
                        for v, d in vals]))
        return salida

    # -- post-proceso de la síntesis --------------------------------------
    def _victimas(self) -> list[str]:
        return sorted({v for d in self.p.documentos for v in d.victimas()}, key=len, reverse=True)

    def _entrecomillar(self, texto: str, lexico: list[EntradaLexico]) -> str:
        for e in lexico:
            for ini, fin, forma in reversed(buscar_termino(texto, e)):
                antes, despues = texto[max(0, ini - 1):ini], texto[fin:fin + 1]
                if antes in ("«", "\"", "“") and despues in ("»", "\"", "”"):
                    continue
                texto = texto[:ini] + f"«{forma}»" + texto[fin:]
        return texto

    def responder(self, consulta: str, k: int | None = None) -> Respuesta:
        p = self.p
        avisos: list[str] = []
        niveles = niveles_permitidos(self.sistema, "publico")
        resultados = p.indice.buscar(consulta, k=k or int(p.config["top_k"]), niveles=niveles)
        umbral = float(p.config.get("puntaje_minimo_asistente", 1.0))
        resultados = [(f, s) for f, s in resultados if s >= umbral]
        fragmentos = [f for f, _ in resultados]
        lexico_corr = self.lexico_vigente()
        lexico = [e for e, _ in lexico_corr]

        notas = {}
        for c in self.correcciones.aceptadas():
            if c["objeto"]["tipo"] in ("documento", "fragmento"):
                notas.setdefault(c["objeto"]["id"], []).append(c)
        documentos = [DocumentoMostrado(_procedencia(f), f.texto, round(s, 3),
                                        notas.get(f.id, []) + notas.get(f.documento.id, []))
                      for f, s in resultados]

        expresiones = []
        for e, ids in lexico_corr:
            donde = [f.id for f in fragmentos if buscar_termino(f.texto, e)]
            if donde:
                expresiones.append(Expresion(e.termino, e.formas(), e.hablante, e.epoca, e.categoria,
                                             e.estigmatizante, e.nota, donde, ids))
        discrepancias = self.discrepancias(fragmentos)
        base = dict(consulta=consulta, sistema=self.sistema.get("nombre", ""), fecha_utc=ahora_utc(),
                    documentos=documentos, expresiones=expresiones, discrepancias=discrepancias)

        if not fragmentos:
            return Respuesta(**base, afirmaciones=[], abstencion=True, motivo_abstencion=(
                "No encontramos respaldo documental en las fuentes públicas del corpus para responder esta "
                f"consulta. Podrían contenerlo {SUGERENCIA_FUENTES}."))

        sistema_txt = instrucciones.ASISTENTE
        usuario = instrucciones.mensaje_con_fragmentos(consulta, fragmentos)
        decision = p.compuerta.revisar(self.sistema, sistema_txt + "\n" + usuario)
        if not decision.permitido:
            return Respuesta(**base, afirmaciones=[], abstencion=True, avisos=[f"Síntesis retenida por la compuerta ética: {decision.motivo}"],
                             motivo_abstencion="La síntesis automática no está disponible para esta consulta. Los documentos se muestran completos.")
        try:
            texto = self.proveedor.generar(Solicitud(sistema_txt, usuario, float(self.sistema.get("temperatura", 0)),
                                                     self.sistema.get("semilla"), int(self.sistema.get("max_tokens", 800))))
        except ErrorProveedor as e:
            return Respuesta(**base, afirmaciones=[], abstencion=True, avisos=[f"El modelo no respondió: {e}"],
                             motivo_abstencion="La síntesis automática falló. Los documentos se muestran completos.")

        entregados = {f.id: f for f in fragmentos}
        pide_nombres = bool(_PIDE_NOMBRES.search(consulta))
        victimas = self._victimas()
        afirmaciones = []
        abstencion = any(a in texto.lower() for a in _FRASES_ABSTENCION)
        for o in dividir_oraciones(texto):
            cs = citas(o)
            validas = [c for c in cs if c in entregados]
            av = [f"cita a un fragmento no entregado: {c}" for c in cs if c not in entregados]
            limpio = o
            if not pide_nombres:
                for v in victimas:
                    if v in limpio:
                        limpio = limpio.replace(v, "[nombre reservado]")
                        av.append("nombre de víctima reservado porque la consulta no lo solicita")
            limpio = self._entrecomillar(limpio, lexico)
            es_abstencion = any(a in o.lower() for a in _FRASES_ABSTENCION)
            if not validas and not es_abstencion:
                av.append("afirmación sin cita verificable")
            afirmaciones.append(Afirmacion(limpio, validas, [_procedencia(entregados[c]) for c in validas],
                                           bool(validas), av))
        if discrepancias:
            avisos.append("Las fuentes recuperadas discrepan en al menos un dato. Revisa la sección de discrepancias.")
        sin_cita = sum(1 for a in afirmaciones if not a.verificada and "afirmación sin cita verificable" in a.avisos)
        if sin_cita:
            avisos.append(f"{sin_cita} afirmación(es) de la síntesis no tienen cita verificable.")
        motivo = ""
        if abstencion:
            motivo = f"El modelo declaró que los fragmentos no bastan. Podrían contenerlo {SUGERENCIA_FUENTES}."
        return Respuesta(**base, afirmaciones=afirmaciones, abstencion=abstencion, motivo_abstencion=motivo,
                         avisos=avisos, texto_modelo=texto)
