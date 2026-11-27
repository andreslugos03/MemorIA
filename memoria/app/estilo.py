"""Apariencia de la interfaz web inspirada en el lenguaje visual de macOS e iOS.

La hoja de estilo complementa el tema de Streamlit (tema_apple.toml) con lo
que el tema no alcanza: barra lateral translúcida con íconos en teselas de
color, títulos grandes, tarjetas, listas agrupadas, control segmentado,
píldoras de estado y tablas. Usa la tipografía del sistema y colores del
sistema en sus variantes clara y oscura. Los íconos son trazos propios y no
reproducen recursos de Apple.
"""
from __future__ import annotations

import html
from urllib.parse import quote

PALETAS = {
    "light": {
        "fondo": "#F5F5F7", "superficie": "#FFFFFF", "superficie-2": "#FAFAFC", "superficie-seg": "#FFFFFF",
        "texto": "#1D1D1F", "texto-2": "#6E6E73", "texto-3": "#86868B",
        "separador": "rgba(60,60,67,0.14)", "relleno": "rgba(118,118,128,0.12)", "relleno-2": "rgba(116,116,128,0.08)",
        "sombra": "0 1px 2px rgba(0,0,0,0.04), 0 6px 20px rgba(0,0,0,0.06)",
        "sombra-suave": "0 1px 2px rgba(0,0,0,0.05)",
        "lateral": "rgba(232,232,237,0.82)",
        "azul": "#007AFF", "verde": "#34C759", "naranja": "#FF9500", "rojo": "#FF3B30", "amarillo": "#FFCC00",
        "morado": "#AF52DE", "indigo": "#5856D6", "teal": "#30B0C7", "gris": "#8E8E93", "marron": "#A2845E",
        "azul-t": "#0040DD", "verde-t": "#248A3D", "naranja-t": "#C93400", "rojo-t": "#D70015", "amarillo-t": "#B25000",
        "morado-t": "#8944AB", "indigo-t": "#3634A3", "teal-t": "#008299", "gris-t": "#6C6C70", "marron-t": "#7F6545",
    },
    "dark": {
        "fondo": "#161617", "superficie": "#232325", "superficie-2": "#2A2A2C", "superficie-seg": "#636366",
        "texto": "#F5F5F7", "texto-2": "#A1A1A6", "texto-3": "#6E6E73",
        "separador": "rgba(84,84,88,0.60)", "relleno": "rgba(118,118,128,0.24)", "relleno-2": "rgba(118,118,128,0.16)",
        "sombra": "0 0 0 0.5px rgba(255,255,255,0.06), 0 8px 24px rgba(0,0,0,0.35)",
        "sombra-suave": "0 0 0 0.5px rgba(255,255,255,0.06)",
        "lateral": "rgba(31,31,33,0.86)",
        "azul": "#0A84FF", "verde": "#30D158", "naranja": "#FF9F0A", "rojo": "#FF453A", "amarillo": "#FFD60A",
        "morado": "#BF5AF2", "indigo": "#5E5CE6", "teal": "#40C8E0", "gris": "#98989D", "marron": "#AC8E68",
        "azul-t": "#409CFF", "verde-t": "#30DB5B", "naranja-t": "#FFB340", "rojo-t": "#FF6961", "amarillo-t": "#FFD426",
        "morado-t": "#DA8FFF", "indigo-t": "#7D7AFF", "teal-t": "#5DE6FF", "gris-t": "#AEAEB2", "marron-t": "#B59469",
    },
}
COLORES = ("azul", "verde", "naranja", "rojo", "amarillo", "morado", "indigo", "teal", "gris", "marron")

# Trazos propios en una retícula de 24 × 24.
ICONOS = {
    "inicio": '<path d="M3.5 11 12 4l8.5 7"/><path d="M6 9.5V20h4.2v-5.5h3.6V20H18V9.5"/>',
    "asistente": '<path d="M4.5 5.5h15v10.5h-9l-4.5 3.8v-3.8H4.5z"/>',
    "correcciones": '<path d="M15 5l4 4L8.5 19.5H4.5v-4z"/><path d="M13 7l4 4"/>',
    "corpus": '<rect x="3.5" y="4.5" width="17" height="4.5" rx="1"/><path d="M5 9v10.5h14V9"/><path d="M10 13h4"/>',
    "ejecutar": '<path d="M8 5.5v13l10-6.5z" fill="currentColor"/>',
    "codificar": ('<path d="M4 6.8l1.6 1.6 2.6-2.8"/><path d="M11.5 7h8.5"/><path d="M4 12.3l1.6 1.6 2.6-2.8"/>'
                  '<path d="M11.5 12.5h8.5"/><path d="M4 17.8l1.6 1.6 2.6-2.8"/><path d="M11.5 18h8.5"/>'),
    "conciliar": '<path d="M7 4v3.5c0 3.2 5 3.8 5 7.5V20"/><path d="M17 4v3.5c0 3.2-5 3.8-5 7.5"/><path d="M9.3 17.4 12 20l2.7-2.6"/>',
    "dictamen": '<circle cx="12" cy="12" r="8.5"/><path d="M8.2 12.3l2.6 2.6 5-5.3"/>',
    "lupa": '<circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5 5"/>',
    "documento": '<path d="M6.5 3.5h7.5l4 4v13h-11.5z"/><path d="M14 3.5v4h4"/><path d="M9.5 12h5M9.5 15.5h5"/>',
    "comillas": '<path d="M6.5 8h4v4c0 2.4-1.4 3.9-4 4.5"/><path d="M13.5 8h4v4c0 2.4-1.4 3.9-4 4.5"/>',
    "alerta": '<path d="M12 4.5 20.5 19.5h-17z"/><path d="M12 10v4.3"/><path d="M12 16.9v.2"/>',
    "chispa": '<path d="M12 4l1.9 4.6L18.5 10.5l-4.6 1.9L12 17l-1.9-4.6L5.5 10.5l4.6-1.9z"/>',
    "escudo": '<path d="M12 3.5 19 6v5.5c0 4.4-3 7.6-7 9-4-1.4-7-4.6-7-9V6z"/><path d="M9 12l2.2 2.2L15.2 10"/>',
    "check": '<path d="M6.5 12.5l3.6 3.6 7.5-8"/>',
    "cruz": '<path d="M7.5 7.5l9 9M16.5 7.5l-9 9"/>',
    "exclamacion": '<path d="M12 6.5v7"/><path d="M12 17.2v.3"/>',
    "menos": '<path d="M7 12h10"/>',
    "carpeta": '<path d="M3.5 7a1.5 1.5 0 0 1 1.5-1.5h4.2l2 2H19a1.5 1.5 0 0 1 1.5 1.5v8.5A1.5 1.5 0 0 1 19 19H5a1.5 1.5 0 0 1-1.5-1.5z"/>',
    "capas": '<path d="M12 4 20.5 8.5 12 13 3.5 8.5z"/><path d="M3.5 12.5 12 17l8.5-4.5"/>',
}

NAVEGACION = [  # página, rótulo, ícono, color de la tesela, sección
    ("Inicio", "Inicio", "inicio", "gris", "Consulta"),
    ("Asistente", "Asistente", "asistente", "azul", None),
    ("Correcciones comunitarias", "Correcciones", "correcciones", "naranja", None),
    ("Corpus y léxico", "Corpus y léxico", "corpus", "marron", None),
    ("Auditoría · ejecutar", "Ejecutar", "ejecutar", "verde", "Auditoría"),
    ("Auditoría · codificar", "Codificar", "codificar", "indigo", None),
    ("Auditoría · conciliar", "Conciliar", "conciliar", "teal", None),
    ("Dictamen", "Dictamen", "dictamen", "morado", None),
]
TIPO_COLOR = {"testimonial": "naranja", "judicial": "indigo", "institucional": "verde", "prensa": "morado"}
ACCESO_COLOR = {"publica": "verde", "restringida": "naranja", "embargada": "rojo"}


def e(t) -> str:
    return html.escape(str(t))


def svg(nombre: str, color: str = "currentColor", tam: int = 16, grosor: float = 2.0) -> str:
    return (f'<svg viewBox="0 0 24 24" width="{tam}" height="{tam}" fill="none" stroke="{color}" '
            f'stroke-width="{grosor}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f'{ICONOS[nombre].replace("currentColor", color)}</svg>')


def _uri(nombre: str, color: str = "#FFFFFF") -> str:
    return "data:image/svg+xml;utf8," + quote(svg(nombre, color, 24, 2.1).replace(' aria-hidden="true"', ' xmlns="http://www.w3.org/2000/svg"'))


def icono_app(tam: int = 40) -> str:
    """Ícono de la aplicación: una tesela con degradado y un archivo con lupa."""
    return (f'<svg width="{tam}" height="{tam}" viewBox="0 0 64 64" aria-hidden="true">'
            '<defs><linearGradient id="apg" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" stop-color="#5AC8FA"/><stop offset=".5" stop-color="#007AFF"/>'
            '<stop offset="1" stop-color="#5856D6"/></linearGradient></defs>'
            '<rect width="64" height="64" rx="14.5" fill="url(#apg)"/>'
            '<g fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M17 18h22l6 6v22H17z" fill="rgba(255,255,255,.16)"/><path d="M23 30h14M23 37h9"/>'
            '<circle cx="40" cy="40" r="7" fill="#007AFF"/><path d="M45 45l5 5"/></g></svg>')


def css(tema: str = "light") -> str:
    p = PALETAS.get(tema, PALETAS["light"])
    variables = ";".join(f"--ap-{k}:{v}" for k, v in p.items())
    pastillas = "".join(
        f".ap-p-{c}{{background:color-mix(in srgb,var(--ap-{c}) {22 if tema == 'dark' else 13}%,transparent);color:var(--ap-{c}-t)}}"
        f".ap-t-{c}{{background:var(--ap-{c})}}.ap-c-{c}{{color:var(--ap-{c}-t)}}" for c in COLORES)
    nav = []
    for i, (_, _, icono, color, seccion) in enumerate(NAVEGACION, start=1):
        caja = f'section[data-testid="stSidebar"] [role="radiogroup"] > div:nth-child({i})'
        nav.append(f'{caja} label::before{{background-color:{p[color]};background-image:url("{_uri(icono)}")}}')
        if seccion and i > 1:
            nav.append(f'{caja}{{margin-top:26px}}{caja} label::after{{content:"{seccion}";position:absolute;top:-20px;left:8px;'
                       'font-size:11px;font-weight:600;color:var(--ap-texto-3);letter-spacing:.01em}')
    primera = NAVEGACION[0][4]
    return f"""<style>
:root{{{variables}}}
html,body,.stApp{{-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;text-rendering:optimizeLegibility}}
.block-container{{max-width:1160px;padding-top:3.4rem;padding-bottom:4rem}}
header[data-testid="stHeader"]{{background:color-mix(in srgb,var(--ap-fondo) 72%,transparent);
  -webkit-backdrop-filter:saturate(180%) blur(20px);backdrop-filter:saturate(180%) blur(20px)}}
[data-testid="stAppDeployButton"],[data-testid="stDecoration"]{{display:none}}
h1{{letter-spacing:-0.028em!important;line-height:1.08!important;padding-bottom:.2rem!important}}
h2,h3,h4{{letter-spacing:-0.016em!important}}
[data-testid="stCaptionContainer"],.stCaption{{color:var(--ap-texto-2)!important}}
.ap-sobretitulo{{font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--ap-texto-3);margin:0 0 -.55rem 2px}}
.ap-subtitulo{{font-size:17px;line-height:1.47;color:var(--ap-texto-2);margin:-.35rem 0 1.7rem;max-width:780px;letter-spacing:-.01em}}

/* Barra lateral translúcida con lista de navegación */
section[data-testid="stSidebar"]{{background:var(--ap-lateral)!important;
  -webkit-backdrop-filter:saturate(180%) blur(30px);backdrop-filter:saturate(180%) blur(30px)}}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"]{{background:transparent}}
.ap-semaforo{{display:flex;gap:8px;margin:0 0 18px 4px}}
.ap-semaforo span{{width:12px;height:12px;border-radius:50%;box-shadow:inset 0 0 0 .5px rgba(0,0,0,.15)}}
.ap-semaforo span:nth-child(1){{background:#FF5F57}}.ap-semaforo span:nth-child(2){{background:#FEBC2E}}.ap-semaforo span:nth-child(3){{background:#28C840}}
.ap-identidad{{display:flex;gap:11px;align-items:center;margin:0 0 20px 4px}}
.ap-identidad svg{{border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.18);flex:none}}
.ap-identidad b{{font-size:15px;font-weight:650;letter-spacing:-.01em;display:block;color:var(--ap-texto)}}
.ap-identidad small{{font-size:12px;color:var(--ap-texto-2)}}
.ap-lateral-seccion{{font-size:11px;font-weight:600;color:var(--ap-texto-3);margin:22px 0 6px 8px}}
section[data-testid="stSidebar"] .st-key-nav,section[data-testid="stSidebar"] .st-key-nav [data-testid="stRadio"]{{width:100%!important}}
section[data-testid="stSidebar"] [role="radiogroup"]{{gap:2px;width:100%;padding-top:20px;position:relative}}
section[data-testid="stSidebar"] [role="radiogroup"] > div{{width:100%}}
section[data-testid="stSidebar"] [role="radiogroup"]::before{{content:"{primera}";position:absolute;top:0;left:8px;
  font-size:11px;font-weight:600;color:var(--ap-texto-3)}}
section[data-testid="stSidebar"] [data-testid="stRadioOption"]{{display:flex;align-items:center;position:relative;
  width:100%;margin:0;padding:5px 8px;border-radius:7px;cursor:default;transition:background .12s ease}}
section[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover{{background:var(--ap-relleno-2)}}
section[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"]{{background:var(--ap-azul)}}
section[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p{{color:#fff!important}}
section[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child{{display:none}}
section[data-testid="stSidebar"] [data-testid="stRadioOption"] p{{font-size:13.5px;font-weight:500;letter-spacing:-.005em}}
section[data-testid="stSidebar"] [data-testid="stRadioOption"]::before{{content:"";flex:none;width:22px;height:22px;margin-right:9px;
  border-radius:6px;background-repeat:no-repeat;background-position:center;background-size:14px;
  box-shadow:inset 0 0 0 .5px rgba(0,0,0,.1)}}
{"".join(nav)}
section[data-testid="stSidebar"] .stTextInput input{{font-size:13px}}

/* Campos, botones y controles */
[data-testid="stTextInputRootElement"],[data-baseweb="select"]>div,.stTextArea textarea,[data-baseweb="textarea"]{{border-radius:10px!important}}
input:focus-visible,textarea:focus-visible{{outline:none}}
[data-testid="stTextInputRootElement"]:focus-within,[data-baseweb="select"]>div:focus-within{{
  box-shadow:0 0 0 3.5px color-mix(in srgb,var(--ap-azul) 35%,transparent)!important;border-color:var(--ap-azul)!important}}
.st-key-consulta [data-testid="stTextInputRootElement"]{{height:56px;border-radius:15px!important;border:none!important;
  background:var(--ap-superficie) url("{_uri('lupa', p['texto-3'])}") no-repeat 18px center/20px!important;
  box-shadow:var(--ap-sombra);padding-left:40px}}
.st-key-consulta input{{font-size:19px!important;letter-spacing:-.01em;background:transparent!important}}
button[data-testid="stBaseButton-primary"],button[data-testid="stBaseButton-primaryFormSubmit"]{{font-weight:600;
  padding:.42rem 1.3rem;border:none;box-shadow:0 1px 2px rgba(0,0,0,.12)}}
button[data-testid="stBaseButton-secondary"],button[data-testid="stBaseButton-secondaryFormSubmit"]{{
  background:var(--ap-superficie);border:.5px solid var(--ap-separador);box-shadow:0 1px 1.5px rgba(0,0,0,.08);font-weight:500}}
[data-testid="stButtonGroup"] [role="toolbar"]:has(button[data-variant="segmented_control"]){{
  display:inline-flex;gap:2px;padding:2px;border-radius:9px;background:var(--ap-relleno)}}
button[data-variant="segmented_control"]{{border:none!important;background:transparent!important;border-radius:7px!important;
  min-height:30px;padding:2px 16px!important;color:var(--ap-texto)!important;box-shadow:none!important}}
button[data-variant="segmented_control"] p{{font-size:13px!important;font-weight:500}}
button[data-variant="segmented_control"][data-selected="true"]{{background:var(--ap-superficie-seg)!important;
  box-shadow:0 3px 8px rgba(0,0,0,.12),0 3px 1px rgba(0,0,0,.04)!important}}
button[data-variant="pills"]{{border:none!important;background:var(--ap-relleno)!important;color:var(--ap-texto)!important}}
button[data-variant="pills"][data-selected="true"]{{background:var(--ap-azul)!important;color:#fff!important}}
button[data-variant="pills"][data-selected="true"] p{{color:#fff!important}}
[data-testid="stMetric"]{{background:var(--ap-superficie);border-radius:18px;padding:16px 18px 14px;box-shadow:var(--ap-sombra)}}
[data-testid="stMetricLabel"] p{{font-size:13px!important;color:var(--ap-texto-2);font-weight:500}}
[data-testid="stMetricValue"]{{font-weight:600!important;letter-spacing:-.025em;font-variant-numeric:tabular-nums}}
[data-testid="stExpander"] details{{border-radius:14px!important;border:.5px solid var(--ap-separador)!important;background:var(--ap-superficie)}}
[data-testid="stForm"]{{border:none!important;border-radius:16px!important;background:var(--ap-superficie);box-shadow:var(--ap-sombra);padding:1.2rem 1.3rem!important}}
[data-testid="stDataFrame"],[data-testid="stDataFrameResizable"]{{border-radius:12px;overflow:hidden;box-shadow:var(--ap-sombra-suave)}}
[data-testid="stAlert"]>div{{border-radius:12px!important}}
[data-testid="stProgress"]>div>div>div{{height:6px!important;border-radius:3px!important}}
[data-testid="stProgress"]>div>div>div>div{{background:var(--ap-azul)!important;border-radius:3px!important}}

/* Componentes propios */
.ap-tarjeta{{background:var(--ap-superficie);border-radius:18px;padding:18px 20px 16px;box-shadow:var(--ap-sombra);margin-bottom:14px}}
.ap-tarjeta h4{{margin:0;padding:0;font-size:17px;font-weight:600;letter-spacing:-.012em;line-height:1.3}}
.ap-meta{{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center;margin:6px 0 10px;font-size:13px;color:var(--ap-texto-2)}}
.ap-cuerpo{{font-size:15px;line-height:1.55;color:var(--ap-texto)}}
.ap-codigo{{font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:12px;color:var(--ap-texto-3)}}
.ap-pastilla{{display:inline-flex;align-items:center;gap:4px;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600;line-height:1.5;white-space:nowrap}}
{pastillas}
.ap-nota{{margin-top:12px;padding:10px 12px;border-radius:10px;background:var(--ap-relleno-2);font-size:13px;color:var(--ap-texto-2)}}
.ap-nota b{{color:var(--ap-texto)}}
.ap-grupo-titulo{{font-size:12px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--ap-texto-2);margin:22px 0 7px 16px}}
.ap-lista{{background:var(--ap-superficie);border-radius:12px;box-shadow:var(--ap-sombra-suave);overflow:hidden;margin-bottom:10px}}
.ap-fila{{display:flex;align-items:center;gap:12px;padding:10px 16px;min-height:46px;position:relative}}
.ap-fila+.ap-fila::before{{content:"";position:absolute;top:0;right:0;left:56px;height:.5px;background:var(--ap-separador)}}
.ap-lista.sin-teselas .ap-fila+.ap-fila::before{{left:16px}}
.ap-tesela{{width:28px;height:28px;border-radius:7px;display:grid;place-items:center;flex:none;color:#fff}}
.ap-fila-texto{{flex:1;min-width:0}}
.ap-fila-titulo{{font-size:15px;color:var(--ap-texto);letter-spacing:-.008em}}
.ap-fila-detalle{{font-size:13px;color:var(--ap-texto-2);margin-top:1px;line-height:1.4}}
.ap-fila-valor{{font-size:15px;color:var(--ap-texto-2);font-variant-numeric:tabular-nums;text-align:right;flex:none}}
.ap-marca{{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;flex:none}}
.ap-marca.hecho{{background:var(--ap-verde);color:#fff}}
.ap-marca.pendiente{{box-shadow:inset 0 0 0 1.6px var(--ap-texto-3)}}
.ap-anillo{{display:flex;align-items:center;gap:14px;margin:4px 0 14px 4px}}
.ap-anillo b{{font-size:22px;font-weight:600;letter-spacing:-.02em;display:block}}
.ap-anillo span{{font-size:13px;color:var(--ap-texto-2)}}
.ap-tabla{{width:100%;border-collapse:separate;border-spacing:0;background:var(--ap-superficie);border-radius:12px;
  box-shadow:var(--ap-sombra-suave);overflow:hidden;font-size:14px;font-variant-numeric:tabular-nums;margin-bottom:12px}}
.ap-tabla,.ap-tabla th,.ap-tabla td{{border:none!important}}
.ap-tabla th{{text-align:left;font-size:12px;font-weight:600;color:var(--ap-texto-2);padding:10px 14px;background:var(--ap-superficie-2);
  border-bottom:.5px solid var(--ap-separador)!important;white-space:nowrap}}
.ap-tabla td{{padding:9px 14px;border-bottom:.5px solid var(--ap-separador)!important;color:var(--ap-texto);vertical-align:middle}}
.ap-tabla tr:last-child td{{border-bottom:none!important}}
.ap-tabla .corto{{white-space:nowrap;color:var(--ap-texto-2)}}
.ap-tabla td.num,.ap-tabla th.num{{text-align:right}}
.ap-tabla tr.ap-tabla-grupo td{{font-weight:600;font-size:13px;background:var(--ap-superficie-2);color:var(--ap-texto-2)}}
.ap-punto{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px;vertical-align:1px}}
.ap-veredicto{{display:flex;gap:14px;align-items:flex-start}}
.ap-veredicto .ap-marca{{width:34px;height:34px;color:#fff}}
.ap-veredicto b{{display:block;font-size:17px;font-weight:650;letter-spacing:-.015em;margin-top:2px}}
.ap-veredicto small{{display:block;font-size:13px;color:var(--ap-texto-2);margin-top:3px;line-height:1.4}}
.ap-estado{{display:flex;align-items:center;gap:10px;padding:12px 16px;border-radius:12px;background:var(--ap-superficie);
  box-shadow:var(--ap-sombra-suave);font-size:14px;margin-bottom:14px}}
.ap-sintesis{{font-size:15px;line-height:1.5;color:var(--ap-texto)}}
.ap-sintesis+.ap-fila-detalle{{margin:2px 0 12px}}
</style>"""


# ---------------------------------------------------------------------------
# Componentes
# ---------------------------------------------------------------------------
def pastilla(texto: str, color: str = "gris") -> str:
    return f'<span class="ap-pastilla ap-p-{color}">{e(texto)}</span>'


def tesela(icono: str, color: str) -> str:
    return f'<span class="ap-tesela ap-t-{color}">{svg(icono, "#fff", 16)}</span>'


def marca(hecho: bool) -> str:
    return f'<span class="ap-marca hecho">{svg("check", "#fff", 14, 2.6)}</span>' if hecho else '<span class="ap-marca pendiente"></span>'


def fila(titulo: str, detalle: str = "", valor: str = "", izquierda: str = "", titulo_html: bool = False) -> str:
    t = titulo if titulo_html else e(titulo)
    d = f'<div class="ap-fila-detalle">{detalle}</div>' if detalle else ""
    v = f'<div class="ap-fila-valor">{valor}</div>' if valor else ""
    return f'<div class="ap-fila">{izquierda}<div class="ap-fila-texto"><div class="ap-fila-titulo">{t}</div>{d}</div>{v}</div>'


def lista(filas: list[str], titulo: str = "", teselas: bool = True) -> str:
    cab = f'<div class="ap-grupo-titulo">{e(titulo)}</div>' if titulo else ""
    clase = "ap-lista" if teselas else "ap-lista sin-teselas"
    return f'{cab}<div class="{clase}">{"".join(filas)}</div>'


def anillo(hechos: int, total: int, color: str = "verde") -> str:
    r, c = 19, 2 * 3.14159 * 19
    fr = hechos / total if total else 0
    return (f'<div class="ap-anillo"><svg width="48" height="48" viewBox="0 0 48 48" aria-hidden="true">'
            f'<circle cx="24" cy="24" r="{r}" fill="none" stroke="var(--ap-relleno)" stroke-width="7"/>'
            f'<circle cx="24" cy="24" r="{r}" fill="none" stroke="var(--ap-{color})" stroke-width="7" stroke-linecap="round" '
            f'stroke-dasharray="{c * fr:.1f} {c:.1f}" transform="rotate(-90 24 24)"/></svg>'
            f'<div><b>{hechos} de {total}</b><span>pasos completos</span></div></div>')


def encabezado(titulo_superior: str) -> str:
    return f'<div class="ap-sobretitulo">{e(titulo_superior)}</div>'


def subtitulo(texto: str) -> str:
    return f'<p class="ap-subtitulo">{e(texto)}</p>'


def estado_dictamen(dictamen: str) -> tuple[str, str]:
    d = dictamen.upper()
    if d.startswith("HABILITADO"):
        return "verde", "check"
    if d.startswith("CONDICIONADO") or d.startswith("EN SUSPENSO"):
        return "naranja", "exclamacion"
    if d.startswith("NO HABILITADO"):
        return "rojo", "cruz"
    return "gris", "menos"


def color_estado(estado: str) -> str:
    if estado.startswith("FALLO"):
        return "rojo"
    if estado == "cumple" or estado == "diagnóstico (cumple)":
        return "verde"
    if estado in ("no cumple", "diagnóstico (no cumple)"):
        return "naranja"
    return "gris"


def tabla(columnas: list[str], filas: list[list[str]], numericas: set[int] = frozenset(), grupos: dict[int, str] | None = None) -> str:
    """Tabla con las celdas ya escapadas o con HTML controlado."""
    th = "".join(f'<th class="{"num" if i in numericas else ""}">{e(c)}</th>' for i, c in enumerate(columnas))
    cuerpo = []
    for n, f in enumerate(filas):
        if grupos and n in grupos:
            cuerpo.append(f'<tr class="ap-tabla-grupo"><td colspan="{len(columnas)}">{e(grupos[n])}</td></tr>')
        cuerpo.append("<tr>" + "".join(f'<td class="{"num" if i in numericas else ""}">{c}</td>' for i, c in enumerate(f)) + "</tr>")
    return f'<table class="ap-tabla"><thead><tr>{th}</tr></thead><tbody>{"".join(cuerpo)}</tbody></table>'


def barra_lateral_cabecera(version: str) -> str:
    return ('<div class="ap-semaforo" aria-hidden="true"><span></span><span></span><span></span></div>'
            f'<div class="ap-identidad">{icono_app(40)}<div><b>MemorIA</b><small>Auditor y asistente · v{e(version)}</small></div></div>')
