"""Interfaz web de MemorIA (Streamlit).

    memoria app ruta/al/proyecto
    streamlit run memoria/app/app.py --theme.base memoria/app/tema_apple.toml

La variable MEMORIA_PROYECTO indica la carpeta del proyecto cuando la app se
abre sin la orden `memoria app`.
"""
from __future__ import annotations

import os
import sys

try:
    import memoria  # noqa: F401
except ImportError:  # ejecución directa desde el repositorio sin instalar
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pandas as pd
import streamlit as st

from memoria import VERSION_PROTOCOLO, __version__
from memoria.app import estilo as ap
from memoria.app.estilo import e
from memoria.asistente import Asistente, ErrorCorreccion, RegistroCorrecciones
from memoria.cegamiento import HOJAS, columnas_hoja, descegar, hojas_codificadas, iniciar_hoja, preparar_hojas, ruta_hoja, validar
from memoria.conciliacion import conciliar
from memoria.ejecucion import ejecutar, leer_registro
from memoria.metricas import PRUEBAS, UMBRALES, calcular, escribir_resultados, fmt, lectura_alfa, reporte_markdown
from memoria.proyecto import Proyecto
from memoria.util import ErrorDatos, escribir_csv, leer_csv

st.set_page_config(page_title="MemorIA", page_icon="◐", layout="wide")


def tema_actual() -> str:
    try:
        return st.context.theme.type or "light"
    except Exception:  # noqa: BLE001 - versiones o entornos sin detección de tema
        return "light"


st.markdown(ap.css(tema_actual()), unsafe_allow_html=True)

PAGINAS = [n[0] for n in ap.NAVEGACION]
ROTULOS = {n[0]: n[1] for n in ap.NAVEGACION}
NOMBRES_HOJAS = {
    "lexica_codificacion": "Léxica · 1b, 1c, 1d", "territorial_dirigida": "Territorial · 2b",
    "fidelidad_afirmaciones": "Fidelidad · afirmaciones 3a", "fidelidad_items": "Fidelidad · ítems trampa 3b, 3c",
    "cuidado_codificacion": "Cuidado · 4a, 4b, 4c",
}
ACCESO = {"publica": "pública", "restringida": "restringida", "embargada": "embargada"}
PRUEBA_ICONO = {"Léxica": ("comillas", "azul"), "Territorial": ("capas", "verde"),
                "Fidelidad": ("documento", "naranja"), "Cuidado": ("escudo", "rojo")}


def marca_proyecto(ruta: str) -> float:
    marcas = []
    for parte in ("corpus", "banco", "sistemas.json", "proyecto.json"):
        r = os.path.join(ruta, parte)
        if os.path.isdir(r):
            marcas += [os.path.getmtime(os.path.join(r, f)) for f in os.listdir(r)]
        elif os.path.exists(r):
            marcas.append(os.path.getmtime(r))
    return max(marcas) if marcas else 0.0


@st.cache_resource(show_spinner=False)
def cargar(ruta: str, _marca: float) -> Proyecto:
    p = Proyecto(ruta)
    _ = p.indice  # construye el índice una vez
    return p


def html(t: str):
    st.markdown(t, unsafe_allow_html=True)


def titulo(seccion: str, texto: str, sub: str = ""):
    html(ap.encabezado(seccion))
    st.title(texto, anchor=False)
    if sub:
        html(ap.subtitulo(sub))


# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------
with st.sidebar:
    html(ap.barra_lateral_cabecera(__version__))
    pagina = st.radio("Sección", PAGINAS, format_func=ROTULOS.get, label_visibility="collapsed", key="nav")
    html('<div class="ap-lateral-seccion">Proyecto</div>')
    ruta = st.text_input("Carpeta del proyecto", value=st.session_state.get("ruta", os.environ.get("MEMORIA_PROYECTO", "")),
                         placeholder="/ruta/al/proyecto", label_visibility="collapsed")
    if st.button("Instalar demostración", key="instalar_demo", width="stretch"):
        from memoria.demo import instalar_demo
        destino = os.path.abspath("memoria_demo")
        instalar_demo(destino, sobrescribir=True)
        st.session_state["ruta"] = destino
        st.rerun()
    st.caption(f"Protocolo de auditoría situada v{VERSION_PROTOCOLO}")

st.session_state["ruta"] = ruta
if not ruta or not os.path.isdir(ruta):
    titulo("Bienvenida", "MemorIA", "Auditoría situada de modelos de lenguaje y asistente de consulta para archivos "
           "testimoniales del conflicto armado. Indica la carpeta de un proyecto en la barra lateral o instala la "
           "demostración con datos ficticios.")
    st.stop()

try:
    p = cargar(os.path.abspath(ruta), marca_proyecto(ruta))
    _ = p.documentos  # valida el corpus al cargar
except (ErrorDatos, OSError, ValueError) as err:
    st.error(f"No se pudo cargar el proyecto. {err}")
    st.stop()


# ---------------------------------------------------------------------------
# Inicio
# ---------------------------------------------------------------------------
def pagina_inicio():
    titulo("Proyecto", p.config.get("nombre", "Proyecto MemorIA"), p.config.get("descripcion", ""))
    niveles = pd.Series([d.nivel_acceso for d in p.documentos]).value_counts()
    c = st.columns(4)
    c[0].metric("Documentos", len(p.documentos))
    c[1].metric("Fuentes públicas", int(niveles.get("publica", 0)))
    c[2].metric("Ítems del banco", len(p.banco))
    c[3].metric("Sistemas", len(p.sistemas))
    reg = leer_registro(p)
    pasos = [
        ("Ejecutar el banco en A y B", "Cada sistema responde sin el archivo y con él", bool(reg)),
        ("Preparar hojas ciegas", "Claves aleatorias en lugar de sistema y condición", os.path.exists(p.ruta_clave)),
        ("Codificar dos veces", "Dos personas, cada una sin ver la otra", all(len(hojas_codificadas(p, h)) >= 2 for h in HOJAS)),
        ("Conciliar", "Una tercera persona resuelve los desacuerdos", all(os.path.exists(ruta_hoja(p, h, "consenso")) for h in HOJAS)),
        ("Descegar y dictaminar", "Indicadores, fiabilidad y dictamen", os.path.exists(os.path.join(p.dir_resultados, "dictamen.json"))),
    ]
    izq, der = st.columns([1, 1], gap="large")
    with izq:
        html('<div class="ap-grupo-titulo">Recorrido de la auditoría</div>')
        html(ap.anillo(sum(ok for *_, ok in pasos), len(pasos)))
        html(ap.lista([ap.fila(t, e(d), izquierda=ap.marca(ok)) for t, d, ok in pasos], teselas=False))
    with der:
        cuentas = {}
        for ind in UMBRALES:
            cuentas[PRUEBAS[ind[0]]] = cuentas.get(PRUEBAS[ind[0]], 0) + 1
        explicacion = {"Léxica": "Las palabras con que la región nombró la violencia",
                       "Territorial": "Todo el territorio y no solo las ciudades",
                       "Fidelidad": "Lo documentado frente a lo inventado",
                       "Cuidado": "Nombres, reserva y responsabilidades"}
        filas = [ap.fila(f"Prueba {n}", e(explicacion[n]), f"{cuentas[n]} indicadores", ap.tesela(*PRUEBA_ICONO[n]))
                 for n in ("Léxica", "Territorial", "Fidelidad", "Cuidado")]
        html(ap.lista(filas, "El protocolo en breve"))
        html('<div class="ap-nota">La condición A es diagnóstica y la B es la única que puede habilitar. La filtración de '
             'fuentes restringidas y la imputación sin soporte son <b>fallos críticos</b> con tolerancia cero. El resultado '
             'es un perfil y no un índice único.</div>')


# ---------------------------------------------------------------------------
# Asistente
# ---------------------------------------------------------------------------
def tarjeta_documento(d):
    pr = d.procedencia
    notas = "".join(f'<div class="ap-nota"><b>Nota comunitaria {e(n["id"])}</b> · {e(n["autoria_colectiva"])} · '
                    f'{e(n["fecha_utc"][:10])}<br>{e(n["texto_propuesto"])}</div>' for n in d.notas_comunitarias)
    html(f'<div class="ap-tarjeta"><h4>{e(pr.titulo)}</h4><div class="ap-meta">'
         f'{ap.pastilla(pr.tipo_fuente, ap.TIPO_COLOR.get(pr.tipo_fuente, "gris"))}'
         f'<span>{e(pr.fecha)}</span><span>·</span><span>{e(pr.municipio)}</span><span>·</span><span>{e(pr.autoria)}</span>'
         f'<span class="ap-codigo">{e(pr.fragmento)}</span></div><div class="ap-cuerpo">{e(d.texto)}</div>{notas}</div>')


def pagina_asistente():
    titulo("Consulta", "Asistente", "El documento va primero. La síntesis automática es una lectura secundaria que siempre "
                                    "se contrasta con las fuentes. Solo se consultan fuentes públicas.")
    consulta = st.text_input("Pregunta", placeholder="¿Qué ocurrió en Puerto Arenal en 1991?", key="consulta",
                             label_visibility="collapsed")
    opciones = ["Simulado"] + [s["nombre"] for s in p.sistemas if s.get("proveedor") != "simulado"]
    sistema = st.segmented_control("Modelo para la síntesis", opciones, default="Simulado", key="modelo_sintesis") or "Simulado"
    if not consulta:
        html(ap.lista([ap.fila(ej, izquierda=ap.tesela("lupa", "azul")) for ej in (
            "¿Qué ocurrió en Puerto Arenal en 1991?", "¿Qué significaba la expresión «Los del Puente»?",
            "¿Qué estableció la sentencia de 2012 sobre San Telmo del Río?")], "Prueba con"))
        return
    asis = Asistente(p, None if sistema == "Simulado" else p.sistema(sistema))
    r = asis.responder(consulta)
    izq, der = st.columns([3, 2], gap="large")
    with izq:
        st.subheader("Documentos", anchor=False)
        if not r.documentos:
            html('<div class="ap-estado">' + ap.tesela("documento", "gris") +
                 'Ningún documento público responde a esta consulta.</div>')
        for d in r.documentos:
            tarjeta_documento(d)
    with der:
        if r.discrepancias:
            filas = []
            for d in r.discrepancias:
                versiones = "<br>".join(f"{e(v['valor'])} · {e(v['tipo_fuente'])}, {e(v['fecha'])} ({e(v['documento'])})"
                                        for v in d.versiones)
                filas.append(ap.fila(f"{d.hecho} · {d.campo}", versiones, izquierda=ap.tesela("alerta", "rojo")))
            html(ap.lista(filas, "Las fuentes discrepan"))
        if r.expresiones:
            filas = []
            for x in r.expresiones:
                detalle = f"Usado por {e(x.hablante)} · {e(x.epoca)}"
                if x.nota:
                    detalle += f"<br>{e(x.nota)}"
                if x.corregida_por:
                    detalle += f"<br>Corregido por {e(', '.join(x.corregida_por))}"
                t = f"«{e(x.termino)}»" + (" " + ap.pastilla("estigmatizante", "rojo") if x.estigmatizante else "")
                filas.append(ap.fila(t, detalle, izquierda=ap.tesela("comillas", "rojo" if x.estigmatizante else "morado"),
                                     titulo_html=True))
            html(ap.lista(filas, "Léxico regional"))
        html('<div class="ap-grupo-titulo">Síntesis</div>')
        partes = []
        if r.abstencion:
            partes.append(f'<div class="ap-sintesis">{e(r.motivo_abstencion)}</div>')
        for a in r.afirmaciones:
            fuentes = "; ".join(f"{pp.tipo_fuente}, {pp.fecha}, {pp.documento}" for pp in a.procedencias)
            pie = (f'<div class="ap-fila-detalle">{e(fuentes)}</div>' if fuentes
                   else f'<div class="ap-fila-detalle">{ap.pastilla("sin cita verificable", "rojo")}</div>')
            partes.append(f'<div class="ap-sintesis">{e(a.texto)}</div>{pie}')
        for av in r.avisos:
            partes.append(f'<div class="ap-fila-detalle">{e(av)}</div>')
        html('<div class="ap-tarjeta">' + "".join(partes) + "</div>")
    with st.expander("Proponer una corrección sobre estos documentos"):
        formulario_correccion([d.procedencia.documento for d in r.documentos] + [x.termino for x in r.expresiones], "asis")


# ---------------------------------------------------------------------------
# Correcciones
# ---------------------------------------------------------------------------
def formulario_correccion(objetivos: list[str], clave: str):
    reg = RegistroCorrecciones(p.ruta_correcciones)
    with st.form(f"corr_{clave}", clear_on_submit=True, border=False):
        autoria = st.text_input("Autoría colectiva", placeholder="Organización, colectivo o comunidad")
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("Sobre qué", ["documento", "fragmento", "lexico", "respuesta"])
        objeto = c2.selectbox("Identificador", objetivos) if objetivos else c2.text_input("Identificador")
        c3, c4 = st.columns(2)
        categoria = c3.selectbox("Categoría", ["lexico", "hecho", "atribucion", "cuidado", "procedencia", "otra"])
        campo = c4.selectbox("Campo del léxico", ["", "hablante", "epoca", "nota", "categoria"],
                             format_func=lambda x: x or "No aplica", help="Solo para correcciones sobre una entrada del léxico")
        texto = st.text_area("Texto propuesto")
        justificacion = st.text_area("Justificación")
        if st.form_submit_button("Registrar propuesta", type="primary"):
            try:
                c = reg.proponer(autoria, tipo, objeto, categoria, texto, justificacion, campo)
                st.success(f"Propuesta {c['id']} registrada el {c['fecha_utc']}.")
            except ErrorCorreccion as err:
                st.error(str(err))


def pagina_correcciones():
    titulo("Consulta", "Correcciones comunitarias", "Cada propuesta y cada resolución queda con fecha y autoría colectiva "
           "en un registro que nunca se reescribe.")
    reg = RegistroCorrecciones(p.ruta_correcciones)
    ok, problemas = reg.verificar()
    if ok:
        html(f'<div class="ap-estado">{ap.tesela("escudo", "verde")}<div><b>Registro íntegro</b><div class="ap-fila-detalle">'
             'Cada entrada lleva el resumen de la anterior.</div></div></div>')
    else:
        html(f'<div class="ap-estado">{ap.tesela("alerta", "rojo")}<div><b>El registro fue alterado</b>'
             f'<div class="ap-fila-detalle">{e(" ".join(problemas))}</div></div></div>')
    estados = reg.estado_actual()
    color = {"propuesta": "azul", "aceptada": "verde", "rechazada": "gris"}
    if estados:
        filas = []
        for c in estados:
            pr = c.propuesta
            detalle = (f"{e(pr['autoria_colectiva'])} · {e(pr['fecha_utc'][:10])} · {e(pr['objeto']['tipo'])} "
                       f"{e(pr['objeto']['id'])}{' · campo ' + e(pr['campo']) if pr.get('campo') else ''}")
            filas.append(ap.fila(f"{pr['id']} · {pr['texto_propuesto']}", detalle, ap.pastilla(c.estado, color[c.estado]),
                                 ap.tesela("correcciones", "naranja")))
        html(ap.lista(filas, "Registro"))
        pendientes = [c.propuesta["id"] for c in estados if c.estado == "propuesta"]
        if pendientes:
            html('<div class="ap-grupo-titulo">Resolución del panel</div>')
            with st.form("resolver", border=False):
                ident = st.selectbox("Corrección", pendientes)
                estado = st.segmented_control("Decisión", ["aceptada", "rechazada"], default="aceptada")
                autoria = st.text_input("Autoría de la resolución", value="Panel de validación")
                motivo = st.text_area("Motivo")
                if st.form_submit_button("Registrar resolución", type="primary"):
                    reg.resolver(ident, estado or "aceptada", autoria, motivo)
                    st.rerun()
    else:
        html('<div class="ap-estado">' + ap.tesela("correcciones", "gris") + "Aún no hay correcciones registradas.</div>")
    html('<div class="ap-grupo-titulo">Nueva propuesta</div>')
    formulario_correccion([d.id for d in p.documentos if d.publico] + [x.termino for x in p.lexico], "pag")


# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------
def pagina_corpus():
    titulo("Consulta", "Corpus y léxico", "Solo los documentos públicos con consentimiento llegan al asistente. Los "
           "restringidos y embargados solo los procesan sistemas locales durante la auditoría.")
    tipos = pd.Series([d.tipo_fuente for d in p.documentos]).value_counts()
    accesos = pd.Series([d.nivel_acceso for d in p.documentos]).value_counts()
    html(" ".join(ap.pastilla(f"{t} {n}", ap.TIPO_COLOR.get(t, "gris")) for t, n in tipos.items()) + "&nbsp;&nbsp;"
         + " ".join(ap.pastilla(f"{ACCESO.get(a, a)} {n}", ap.ACCESO_COLOR.get(a, "gris")) for a, n in accesos.items()))
    st.write("")
    st.dataframe(pd.DataFrame([{
        "id": d.id, "título": d.titulo, "tipo": d.tipo_fuente, "fecha": d.fecha, "municipio": d.municipio,
        "acceso": ACCESO.get(d.nivel_acceso, d.nivel_acceso), "consentimiento IA": "sí" if d.consentimiento_ia else "no",
    } for d in p.documentos]), hide_index=True, width="stretch")
    st.subheader("Léxico regional", anchor=False)
    filas = []
    for x in p.lexico:
        detalle = f"Usado por {e(x.hablante)} · {e(x.epoca)} · {e(x.categoria)}" + (f"<br>{e(x.nota)}" if x.nota else "")
        t = f"«{e(x.termino)}»" + (" " + ap.pastilla("estigmatizante", "rojo") if x.estigmatizante else "")
        filas.append(ap.fila(t, detalle, izquierda=ap.tesela("comillas", "rojo" if x.estigmatizante else "morado"), titulo_html=True))
    html(ap.lista(filas))


# ---------------------------------------------------------------------------
# Auditoría
# ---------------------------------------------------------------------------
def pagina_ejecutar():
    titulo("Auditoría", "Ejecutar el banco", "Cada sistema responde el banco sin el archivo (condición A) y con "
           "recuperación sobre el corpus (condición B). Las compuertas éticas retienen lo que no debe salir.")
    if not p.sistemas:
        st.warning("El proyecto no declara sistemas en sistemas.json.")
        return
    nombres_todos = [s["nombre"] for s in p.sistemas]
    nombres = st.pills("Sistemas", nombres_todos, selection_mode="multi", default=nombres_todos, key="sistemas_sel")
    condiciones = st.segmented_control("Condiciones", ["A", "B"], selection_mode="multi", default=["A", "B"], key="cond_sel")
    estabilidad = st.toggle("Submuestra de estabilidad (20 % de los ítems, cinco repeticiones a temperatura 0,7)")
    if st.button("Ejecutar", type="primary", disabled=not (nombres and condiciones), key="ejecutar"):
        barra = st.progress(0.0, text="Ejecutando")
        filas = ejecutar(p, list(nombres), tuple(sorted(condiciones)), estabilidad,
                         progreso=lambda i, n: barra.progress(i / n, text=f"{i} de {n} ejecuciones"))
        st.success(f"{len(filas)} ejecuciones registradas.")
    reg = leer_registro(p)
    if not reg:
        return
    df = pd.DataFrame(reg)
    filas = []
    for (m, c), g in df.groupby(["modelo", "condicion"]):
        cuenta = g["estado"].value_counts()
        valor = " ".join(ap.pastilla(f"{k} {int(v)}", {"ok": "verde", "retenida": "naranja", "error": "rojo"}.get(k, "gris"))
                         for k, v in cuenta.items())
        s = next((x for x in p.sistemas if x["nombre"] == m), {})
        lugar = "local" if str(g["local"].iloc[0]) == "1" else "externo"
        detalle = f"Condición {e(c)} · {lugar} · {e(s.get('version_modelo', s.get('modelo', '')))}"
        filas.append(ap.fila(m, detalle, valor, ap.tesela("ejecutar", "verde")))
    html(ap.lista(filas, "Registro de ejecuciones"))
    otras = df[df["estado"] != "ok"]
    if len(otras):
        filas = []
        for r in otras.itertuples():
            retenida = r.estado == "retenida"
            filas.append(ap.fila(f"{r.modelo} · {r.id_item} · condición {r.condicion}", e(r.detalle),
                                 ap.pastilla(r.estado, "naranja" if retenida else "rojo"),
                                 ap.tesela("escudo" if retenida else "alerta", "naranja" if retenida else "rojo")))
        html(ap.lista(filas, "Retenidas por las compuertas o con error"))


def pagina_codificar():
    titulo("Auditoría", "Codificación ciega", "Las hojas no muestran sistema ni condición. La clave de cegamiento queda "
           "en custodia de una persona ajena a la codificación.")
    if st.button("Preparar hojas ciegas a partir del registro", key="preparar"):
        r = preparar_hojas(p)
        st.success("Hojas preparadas. " + ", ".join(f"{k} {v}" for k, v in r.items()))
    if not os.path.exists(os.path.join(p.dir_plantillas, "cuidado_codificacion.csv")):
        st.caption("Aún no hay hojas ciegas.")
        return
    c1, c2 = st.columns([3, 2])
    hoja = c1.selectbox("Hoja", list(HOJAS), format_func=NOMBRES_HOJAS.get)
    codificador = c2.text_input("Tu identificador de codificador", placeholder="cod1", key="codificador")
    if not codificador:
        return
    ruta_h = iniciar_hoja(p, hoja, codificador)
    df = pd.DataFrame(leer_csv(ruta_h), columns=columnas_hoja(hoja)).fillna("")
    variables = HOJAS[hoja]["variables"] + ["observaciones"]
    st.caption("Solo se editan las columnas de codificación. "
               + ("Puedes partir o agregar afirmaciones con nuevas filas." if hoja == "fidelidad_afirmaciones" else ""))
    editado = st.data_editor(df, disabled=[c for c in df.columns if c not in variables and
                                            not (hoja == "fidelidad_afirmaciones" and c in ("id_afirmacion", "texto_afirmacion"))],
                             num_rows="dynamic" if hoja == "fidelidad_afirmaciones" else "fixed",
                             hide_index=True, width="stretch", key=f"ed_{hoja}_{codificador}")
    if st.button("Guardar codificación", type="primary", key="guardar_codificacion"):
        filas = editado.fillna("").astype(str).to_dict("records")
        for f in filas:
            f["codificador"] = codificador
        errores = validar(hoja, filas)
        if errores:
            st.error("Revisa estos valores antes de guardar. " + " · ".join(errores[:12]))
        else:
            escribir_csv(ruta_h, filas, columnas_hoja(hoja))
            st.success(f"Guardado en {ruta_h}")


def pagina_conciliar():
    titulo("Auditoría", "Conciliación", "Los acuerdos pasan solos a la hoja de consenso. Los desacuerdos quedan en "
           "blanco para que una tercera persona del panel los resuelva.")
    hoja = st.selectbox("Hoja", list(HOJAS), format_func=NOMBRES_HOJAS.get)
    sobrescribir = st.toggle("Rehacer la hoja de consenso desde cero")
    r = conciliar(p, hoja, sobrescribir)
    if r.get("aviso"):
        html('<div class="ap-estado">' + ap.tesela("conciliar", "gris") + e(r["aviso"]) + "</div>")
        return
    color = {"aceptable": "verde", "tentativa": "naranja", "n/d": "gris"}
    filas = [[e(a["variable"]), e(a["nivel"]), a["alfa"], ap.pastilla(a["lectura"], color.get(a["lectura"], "rojo"))]
             for a in r["alfas"]]
    html('<div class="ap-grupo-titulo">Fiabilidad preliminar</div>' + ap.tabla(["Variable", "Nivel", "Alfa", "Lectura"], filas, {2}))
    n = len(r["desacuerdos"])
    st.caption(f"{n} {'desacuerdo' if n == 1 else 'desacuerdos'} entre {', '.join(r['codificadores'])}.")
    ruta_c = ruta_hoja(p, hoja, "consenso")
    df = pd.DataFrame(leer_csv(ruta_c), columns=columnas_hoja(hoja)).fillna("")
    variables = HOJAS[hoja]["variables"] + ["observaciones"]
    editado = st.data_editor(df, disabled=[c for c in df.columns if c not in variables], hide_index=True,
                             width="stretch", key=f"cons_{hoja}")
    if st.button("Guardar consenso", type="primary", key="guardar_consenso"):
        filas = editado.fillna("").astype(str).to_dict("records")
        errores = validar(hoja, filas)
        if errores:
            st.error(" · ".join(errores[:12]))
        else:
            escribir_csv(ruta_c, filas, columnas_hoja(hoja))
            st.success("Consenso guardado.")


def pagina_dictamen():
    titulo("Auditoría", "Dictamen", "Un perfil por sistema y condición. El protocolo no reúne los indicadores en un "
           "índice único, porque esa cifra ocultaría qué falla y ante quién.")
    if st.button("Descegar y calcular", type="primary", key="calcular"):
        descegar(p)
        escribir_resultados(calcular(p.dir_datos), p.dir_resultados)
    if not os.path.isdir(p.dir_datos):
        st.caption("Aún no hay datos descegados.")
        return
    calc = calcular(p.dir_datos)
    if not calc["dictamenes"]:
        st.info("No hay indicadores calculables todavía.")
        return
    items = list(calc["dictamenes"].items())
    for i in range(0, len(items), 2):
        cols = st.columns(2)
        for col, ((m, c), d) in zip(cols, items[i:i + 2]):
            color, icono = ap.estado_dictamen(d["dictamen"])
            obs = "".join(f'<div class="ap-fila-detalle" style="margin-top:6px">{e(o)}</div>' for o in d["observaciones"])
            col.markdown(f'<div class="ap-tarjeta"><div class="ap-veredicto"><span class="ap-marca ap-t-{color}">'
                         f'{ap.svg(icono, "#fff", 18, 2.6)}</span><div><span class="ap-fila-detalle">{e(m)} · condición {e(c)}</span>'
                         f'<b class="ap-c-{color}">{e(d["dictamen"])}</b><small>{e(d["detalle"])}</small>{obs}</div></div></div>',
                         unsafe_allow_html=True)
    sistemas = list(calc["dictamenes"])
    valores = {(x["modelo"], x["condicion"], x["indicador"]): x for x in calc["filas"]}
    filas, grupos, prueba_previa = [], {}, None
    for ind in UMBRALES:
        prueba = PRUEBAS[ind[0]]
        if prueba != prueba_previa:
            grupos[len(filas)] = f"Prueba {prueba}"
            prueba_previa = prueba
        codigo, *nombre = ind.split("_")
        umbral = valores[(sistemas[0][0], sistemas[0][1], ind)]["umbral"].replace(">=", "≥").replace("<=", "≤")
        celdas = [f"<b>{e(codigo)}</b> {e(' '.join(nombre))}", f'<span class="corto">{e(umbral)}</span>']
        for m, c in sistemas:
            x = valores[(m, c, ind)]
            celdas.append(f'<span class="ap-punto ap-t-{ap.color_estado(x["estado"])}" title="{e(x["estado"])}"></span>{e(x["valor"])}')
        filas.append(celdas)
    html('<div class="ap-grupo-titulo">Perfil de indicadores</div>'
         + ap.tabla(["Indicador", "Umbral"] + [f"{m} · {c}" for m, c in sistemas], filas, set(range(2, 2 + len(sistemas))), grupos))
    st.caption("Verde cumple · naranja no cumple · rojo fallo crítico · gris sin datos o no aplica.")
    if calc["efecto"]:
        filas = [[e(x["modelo"]), e(x["indicador"]), x["valor_A"], x["valor_B"], f"<b>{e(x['efecto_B_menos_A'])}</b>"]
                 for x in calc["efecto"]]
        html('<div class="ap-grupo-titulo">Efecto correctivo del corpus</div>'
             + ap.tabla(["Sistema", "Indicador", "A", "B", "B − A"], filas, {2, 3, 4}))
    color = {"aceptable": "verde", "tentativa": "naranja", "n/d": "gris"}
    filas = [[e(a), e(b), e(c), fmt(d), ap.pastilla(lectura_alfa(d), color.get(lectura_alfa(d), "rojo"))]
             for a, b, c, d in calc["fiabilidad"]]
    html('<div class="ap-grupo-titulo">Fiabilidad entre codificadores</div>'
         + ap.tabla(["Prueba", "Variable", "Nivel", "Alfa", "Lectura"], filas, {3}))
    st.download_button("Descargar reporte", reporte_markdown(calc), "reporte_auditoria.md", key="descargar")


{
    "Inicio": pagina_inicio, "Asistente": pagina_asistente, "Correcciones comunitarias": pagina_correcciones,
    "Corpus y léxico": pagina_corpus, "Auditoría · ejecutar": pagina_ejecutar, "Auditoría · codificar": pagina_codificar,
    "Auditoría · conciliar": pagina_conciliar, "Dictamen": pagina_dictamen,
}[pagina]()
