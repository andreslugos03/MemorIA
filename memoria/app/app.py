"""Interfaz web de MemorIA (Streamlit).

    memoria app ruta/al/proyecto
    streamlit run memoria/app/app.py      (lee la variable MEMORIA_PROYECTO)
"""
from __future__ import annotations

import html
import os
import sys

try:
    import memoria  # noqa: F401
except ImportError:  # ejecución directa desde el repositorio sin instalar
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pandas as pd
import streamlit as st

from memoria import VERSION_PROTOCOLO, __version__
from memoria.app.estilo import CSS, pastilla
from memoria.asistente import Asistente, ErrorCorreccion, RegistroCorrecciones
from memoria.cegamiento import HOJAS, columnas_hoja, descegar, hojas_codificadas, iniciar_hoja, preparar_hojas, ruta_hoja, validar
from memoria.conciliacion import conciliar
from memoria.ejecucion import ejecutar, leer_registro
from memoria.metricas import calcular, escribir_resultados, reporte_markdown
from memoria.proyecto import Proyecto
from memoria.util import ErrorDatos, escribir_csv, leer_csv

st.set_page_config(page_title="MemorIA", page_icon="◐", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

PAGINAS = ["Inicio", "Asistente", "Correcciones comunitarias", "Corpus y léxico",
           "Auditoría · ejecutar", "Auditoría · codificar", "Auditoría · conciliar", "Dictamen"]
NOMBRES_HOJAS = {
    "lexica_codificacion": "Léxica (1b, 1c, 1d)", "territorial_dirigida": "Territorial dirigida (2b)",
    "fidelidad_afirmaciones": "Fidelidad, afirmaciones (3a)", "fidelidad_items": "Fidelidad, ítems trampa (3b, 3c)",
    "cuidado_codificacion": "Cuidado (4a, 4b, 4c)",
}


def e(t) -> str:
    return html.escape(str(t))


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
    p.indice  # construye el índice una vez  # noqa: B018
    return p


# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### MemorIA")
    st.caption(f"Auditor y asistente v{__version__} · protocolo v{VERSION_PROTOCOLO}")
    ruta = st.text_input("Carpeta del proyecto", value=st.session_state.get("ruta", os.environ.get("MEMORIA_PROYECTO", "")))
    if st.button("Instalar demostración ficticia"):
        from memoria.demo import instalar_demo
        destino = os.path.abspath("memoria_demo")
        instalar_demo(destino, sobrescribir=True)
        st.session_state["ruta"] = destino
        st.rerun()
    pagina = st.radio("Sección", PAGINAS, label_visibility="collapsed")

st.session_state["ruta"] = ruta
if not ruta or not os.path.isdir(ruta):
    st.title("MemorIA")
    st.write("Indica la carpeta de un proyecto en la barra lateral o instala la demostración con datos ficticios.")
    st.stop()

try:
    p = cargar(os.path.abspath(ruta), marca_proyecto(ruta))
    p.documentos  # noqa: B018 - valida el corpus al cargar
except (ErrorDatos, OSError, ValueError) as err:
    st.error(f"No se pudo cargar el proyecto. {err}")
    st.stop()


# ---------------------------------------------------------------------------
def pagina_inicio():
    st.title(p.config.get("nombre", "Proyecto MemorIA"))
    if p.config.get("descripcion"):
        st.caption(p.config["descripcion"])
    niveles = pd.Series([d.nivel_acceso for d in p.documentos]).value_counts()
    c = st.columns(4)
    c[0].metric("Documentos", len(p.documentos))
    c[1].metric("Públicos", int(niveles.get("publica", 0)))
    c[2].metric("Ítems del banco", len(p.banco))
    c[3].metric("Sistemas", len(p.sistemas))
    reg = leer_registro(p)
    hechos = {
        "Ejecutar el banco en A y B": bool(reg),
        "Preparar hojas ciegas": os.path.exists(p.ruta_clave),
        "Codificar (dos codificadores)": all(len(hojas_codificadas(p, h)) >= 2 for h in HOJAS),
        "Conciliar": all(os.path.exists(ruta_hoja(p, h, "consenso")) for h in HOJAS),
        "Descegar y dictaminar": os.path.exists(os.path.join(p.dir_resultados, "dictamen.json")),
    }
    st.subheader("Recorrido de la auditoría")
    for paso, ok in hechos.items():
        st.markdown(f"{'●' if ok else '○'} {paso}")
    st.subheader("El protocolo en breve")
    st.write("Cuatro pruebas (léxica, territorial, fidelidad y cuidado) con veintiún indicadores y umbrales explícitos. "
             "Cada sistema responde sin el archivo (condición A, diagnóstica) y con recuperación sobre el corpus "
             "(condición B, la única que puede habilitar). La filtración de fuentes restringidas y la imputación sin "
             "soporte son fallos críticos con tolerancia cero. El resultado es un perfil y no un índice único.")


def tarjeta_documento(d, i):
    pr = d.procedencia
    notas = "".join(f'<div class="mi-nota">Nota comunitaria {e(n["id"])} · {e(n["autoria_colectiva"])} · '
                    f'{e(n["fecha_utc"][:10])}<br>{e(n["texto_propuesto"])}</div>' for n in d.notas_comunitarias)
    st.markdown(
        f'<div class="mi-tarjeta"><div class="mi-titulo">{i}. {e(pr.titulo)}</div>'
        f'<div class="mi-ficha">{pastilla(e(pr.tipo_fuente), "p-" + pr.tipo_fuente)}{e(pr.fecha)} · {e(pr.municipio)} · '
        f'{e(pr.autoria)} · <code>{e(pr.fragmento)}</code></div><div>{e(d.texto)}</div>{notas}</div>',
        unsafe_allow_html=True)


def pagina_asistente():
    st.title("Asistente de consulta")
    st.caption("El documento va primero. La síntesis automática es una lectura secundaria que siempre se contrasta con las fuentes. "
               "Solo se consultan fuentes públicas.")
    opciones = ["simulado (sin red)"] + [s["nombre"] for s in p.sistemas if s.get("proveedor") != "simulado"]
    sistema = st.selectbox("Modelo para la síntesis", opciones)
    consulta = st.text_input("Pregunta", placeholder="¿Qué ocurrió en Puerto Arenal en 1991?", key="consulta")
    if not consulta:
        return
    asis = Asistente(p, None if sistema.startswith("simulado") else p.sistema(sistema))
    r = asis.responder(consulta)
    izq, der = st.columns([3, 2], gap="large")
    with izq:
        st.subheader("Documentos")
        if not r.documentos:
            st.info("Ningún documento público responde a esta consulta.")
        for i, d in enumerate(r.documentos, start=1):
            tarjeta_documento(d, i)
    with der:
        if r.discrepancias:
            st.subheader("Las fuentes discrepan")
            for d in r.discrepancias:
                versiones = "<br>".join(f"{e(v['valor'])} · {e(v['tipo_fuente'])}, {e(v['fecha'])} ({e(v['documento'])})"
                                        for v in d.versiones)
                st.markdown(f'<div class="mi-tarjeta">{pastilla("discrepancia", "p-alerta")}<b>{e(d.hecho)} · {e(d.campo)}</b>'
                            f'<div class="mi-ficha" style="margin-top:.4rem">{versiones}</div></div>', unsafe_allow_html=True)
        if r.expresiones:
            st.subheader("Léxico regional")
            for x in r.expresiones:
                marca = pastilla("estigmatizante", "p-alerta") if x.estigmatizante else ""
                corr = f"<div class='mi-ficha'>Corregido por {e(', '.join(x.corregida_por))}</div>" if x.corregida_por else ""
                st.markdown(f'<div class="mi-tarjeta"><b>«{e(x.termino)}»</b> {marca}<div class="mi-ficha">'
                            f'Usado por {e(x.hablante)} · {e(x.epoca)}</div><div class="mi-sintesis">{e(x.nota)}</div>{corr}</div>',
                            unsafe_allow_html=True)
        st.subheader("Síntesis")
        if r.abstencion:
            st.warning(r.motivo_abstencion)
        for a in r.afirmaciones:
            fuentes = "; ".join(f"{pp.tipo_fuente}, {pp.fecha}, {pp.documento}" for pp in a.procedencias)
            estado = f'<div class="mi-ficha">{e(fuentes)}</div>' if fuentes else pastilla("sin cita verificable", "p-alerta")
            st.markdown(f'<div class="mi-sintesis">{e(a.texto)}</div>{estado}', unsafe_allow_html=True)
        for av in r.avisos:
            st.caption(av)
    with st.expander("Proponer una corrección sobre estos documentos"):
        formulario_correccion([d.procedencia.documento for d in r.documentos] + [x.termino for x in r.expresiones], "asis")


def formulario_correccion(objetivos: list[str], clave: str):
    reg = RegistroCorrecciones(p.ruta_correcciones)
    with st.form(f"corr_{clave}", clear_on_submit=True):
        autoria = st.text_input("Autoría colectiva (organización, colectivo o comunidad)")
        tipo = st.selectbox("Sobre qué", ["documento", "fragmento", "lexico", "respuesta"])
        objeto = st.selectbox("Identificador", objetivos) if objetivos else st.text_input("Identificador")
        categoria = st.selectbox("Categoría", ["lexico", "hecho", "atribucion", "cuidado", "procedencia", "otra"])
        campo = st.selectbox("Campo del léxico (solo para correcciones de léxico)", ["", "hablante", "epoca", "nota", "categoria"])
        texto = st.text_area("Texto propuesto")
        justificacion = st.text_area("Justificación")
        if st.form_submit_button("Registrar propuesta"):
            try:
                c = reg.proponer(autoria, tipo, objeto, categoria, texto, justificacion, campo)
                st.success(f"Propuesta {c['id']} registrada el {c['fecha_utc']}.")
            except ErrorCorreccion as err:
                st.error(str(err))


def pagina_correcciones():
    st.title("Correcciones comunitarias")
    reg = RegistroCorrecciones(p.ruta_correcciones)
    ok, problemas = reg.verificar()
    if ok:
        st.caption("Registro íntegro. Cada entrada lleva fecha, autoría colectiva y el resumen de la entrada anterior.")
    else:
        st.error("El registro fue alterado. " + " ".join(problemas))
    estados = reg.estado_actual()
    if estados:
        st.dataframe(pd.DataFrame([{
            "id": c.propuesta["id"], "estado": c.estado, "fecha": c.propuesta["fecha_utc"][:10],
            "autoría colectiva": c.propuesta["autoria_colectiva"], "objeto": f"{c.propuesta['objeto']['tipo']} {c.propuesta['objeto']['id']}",
            "categoría": c.propuesta["categoria"], "campo": c.propuesta.get("campo", ""), "propuesta": c.propuesta["texto_propuesto"],
        } for c in estados]), hide_index=True, width="stretch")
        pendientes = [c.propuesta["id"] for c in estados if c.estado == "propuesta"]
        if pendientes:
            st.subheader("Resolución del panel")
            with st.form("resolver"):
                ident = st.selectbox("Corrección", pendientes)
                estado = st.radio("Decisión", ["aceptada", "rechazada"], horizontal=True)
                autoria = st.text_input("Autoría de la resolución", value="Panel de validación")
                motivo = st.text_area("Motivo")
                if st.form_submit_button("Registrar resolución"):
                    reg.resolver(ident, estado, autoria, motivo)
                    st.rerun()
    else:
        st.info("Aún no hay correcciones registradas.")
    st.subheader("Nueva propuesta")
    formulario_correccion([d.id for d in p.documentos if d.publico] + [x.termino for x in p.lexico], "pag")


def pagina_corpus():
    st.title("Corpus y léxico")
    st.dataframe(pd.DataFrame([{
        "id": d.id, "título": d.titulo, "tipo": d.tipo_fuente, "fecha": d.fecha, "municipio": d.municipio,
        "acceso": d.nivel_acceso, "consentimiento IA": "sí" if d.consentimiento_ia else "no",
    } for d in p.documentos]), hide_index=True, width="stretch")
    st.caption("Solo los documentos públicos con consentimiento llegan al asistente. Los restringidos y embargados solo "
               "los procesan sistemas locales durante la auditoría.")
    st.subheader("Léxico regional")
    st.dataframe(pd.DataFrame([{"término": x.termino, "variantes": "; ".join(x.variantes), "hablante": x.hablante,
                                "época": x.epoca, "categoría": x.categoria, "estigmatizante": "sí" if x.estigmatizante else "no",
                                "nota": x.nota} for x in p.lexico]), hide_index=True, width="stretch")


def pagina_ejecutar():
    st.title("Ejecutar el banco de ítems")
    if not p.sistemas:
        st.warning("El proyecto no declara sistemas en sistemas.json.")
        return
    nombres = st.multiselect("Sistemas", [s["nombre"] for s in p.sistemas], default=[s["nombre"] for s in p.sistemas])
    condiciones = st.multiselect("Condiciones", ["A", "B"], default=["A", "B"])
    estabilidad = st.checkbox("Agregar la submuestra de estabilidad (20 % de los ítems, cinco repeticiones a temperatura 0,7)")
    if st.button("Ejecutar", type="primary", disabled=not (nombres and condiciones)):
        barra = st.progress(0.0, text="Ejecutando")
        filas = ejecutar(p, nombres, tuple(condiciones), estabilidad,
                         progreso=lambda i, n: barra.progress(i / n, text=f"{i} de {n} ejecuciones"))
        st.success(f"{len(filas)} ejecuciones registradas.")
    reg = leer_registro(p)
    if reg:
        df = pd.DataFrame(reg)
        st.dataframe(df.groupby(["modelo", "condicion", "estado"]).size().rename("ejecuciones").reset_index(),
                     hide_index=True)
        otras = df[df["estado"] != "ok"]
        if len(otras):
            st.subheader("Ejecuciones retenidas o con error")
            st.dataframe(otras[["modelo", "id_item", "condicion", "estado", "detalle"]], hide_index=True, width="stretch")


def pagina_codificar():
    st.title("Codificación ciega")
    if st.button("Preparar hojas ciegas a partir del registro"):
        r = preparar_hojas(p)
        st.success("Hojas preparadas. " + ", ".join(f"{k} {v}" for k, v in r.items()))
        st.info("La clave de cegamiento quedó en codificacion/custodia. Debe custodiarla una persona ajena a la codificación.")
    if not os.path.exists(os.path.join(p.dir_plantillas, "cuidado_codificacion.csv")):
        st.caption("Aún no hay hojas ciegas.")
        return
    hoja = st.selectbox("Hoja", list(HOJAS), format_func=NOMBRES_HOJAS.get)
    codificador = st.text_input("Tu identificador de codificador", placeholder="cod1", key="codificador")
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
    st.title("Conciliación")
    hoja = st.selectbox("Hoja", list(HOJAS), format_func=NOMBRES_HOJAS.get)
    sobrescribir = st.checkbox("Rehacer la hoja de consenso desde cero")
    r = conciliar(p, hoja, sobrescribir)
    if r.get("aviso"):
        st.info(r["aviso"])
        return
    st.dataframe(pd.DataFrame(r["alfas"]), hide_index=True)
    st.caption(f"{len(r['desacuerdos'])} desacuerdos entre {', '.join(r['codificadores'])}. Los acuerdos ya están en la hoja de consenso.")
    ruta_c = ruta_hoja(p, hoja, "consenso")
    df = pd.DataFrame(leer_csv(ruta_c), columns=columnas_hoja(hoja)).fillna("")
    variables = HOJAS[hoja]["variables"] + ["observaciones"]
    editado = st.data_editor(df, disabled=[c for c in df.columns if c not in variables], hide_index=True,
                             width="stretch", key=f"cons_{hoja}")
    if st.button("Guardar consenso", type="primary"):
        filas = editado.fillna("").astype(str).to_dict("records")
        errores = validar(hoja, filas)
        if errores:
            st.error(" · ".join(errores[:12]))
        else:
            escribir_csv(ruta_c, filas, columnas_hoja(hoja))
            st.success("Consenso guardado.")


def pagina_dictamen():
    st.title("Dictamen")
    if st.button("Descegar y calcular", type="primary"):
        descegar(p)
        escribir_resultados(calcular(p.dir_datos), p.dir_resultados)
    if not os.path.isdir(p.dir_datos):
        st.caption("Aún no hay datos descegados.")
        return
    calc = calcular(p.dir_datos)
    if not calc["dictamenes"]:
        st.info("No hay indicadores calculables todavía.")
        return
    cols = st.columns(max(1, len(calc["dictamenes"])))
    for col, ((m, c), d) in zip(cols, calc["dictamenes"].items()):
        clase = "dic-" + d["dictamen"].split()[0]
        col.markdown(f'<div class="mi-tarjeta"><div class="mi-ficha">{e(m)} · condición {e(c)}</div>'
                     f'<div class="mi-titulo {clase}">{e(d["dictamen"])}</div><div class="mi-ficha">{e(d["detalle"])}</div></div>',
                     unsafe_allow_html=True)
    df = pd.DataFrame(calc["filas"])
    df["sistema"] = df["modelo"] + " · " + df["condicion"]
    tabla = df.pivot_table(index=["prueba", "indicador", "umbral"], columns="sistema", values="valor", aggfunc="first")
    st.subheader("Perfil de indicadores")
    st.dataframe(tabla, width="stretch")
    with st.expander("Estado de cada indicador"):
        st.dataframe(df.pivot_table(index=["prueba", "indicador"], columns="sistema", values="estado", aggfunc="first"),
                     width="stretch")
    if calc["efecto"]:
        st.subheader("Efecto correctivo del corpus (B menos A)")
        st.dataframe(pd.DataFrame(calc["efecto"]), hide_index=True, width="stretch")
    st.subheader("Fiabilidad entre codificadores")
    st.dataframe(pd.DataFrame([{"prueba": a, "variable": b, "nivel": c, "alfa": "n/d" if d != d else round(d, 3)}
                               for a, b, c, d in calc["fiabilidad"]]), hide_index=True)
    st.download_button("Descargar reporte (Markdown)", reporte_markdown(calc), "reporte_auditoria.md")


{
    "Inicio": pagina_inicio, "Asistente": pagina_asistente, "Correcciones comunitarias": pagina_correcciones,
    "Corpus y léxico": pagina_corpus, "Auditoría · ejecutar": pagina_ejecutar, "Auditoría · codificar": pagina_codificar,
    "Auditoría · conciliar": pagina_conciliar, "Dictamen": pagina_dictamen,
}[pagina]()
