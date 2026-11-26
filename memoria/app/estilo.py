"""Estilo visual sobrio para la interfaz Streamlit."""

CSS = """
<style>
html, body, [class*="css"] {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", "Segoe UI", Roboto, sans-serif;
}
h1, h2, h3 { letter-spacing: -0.02em; font-weight: 650; }
.block-container { padding-top: 2.2rem; max-width: 1180px; }
section[data-testid="stSidebar"] { background: rgba(246, 246, 248, 0.92); backdrop-filter: blur(18px); }
.mi-tarjeta {
  border: 1px solid rgba(0,0,0,0.08); border-radius: 16px; padding: 1rem 1.15rem; margin-bottom: 0.8rem;
  background: #ffffff; box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 4px 14px rgba(0,0,0,0.04);
}
.mi-ficha { color: #6e6e73; font-size: 0.82rem; margin-bottom: 0.35rem; }
.mi-titulo { font-weight: 640; font-size: 1.02rem; margin-bottom: 0.15rem; }
.mi-pastilla {
  display: inline-block; padding: 0.12rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600;
  margin-right: 0.35rem; background: #f2f2f7; color: #1d1d1f;
}
.p-testimonial { background: #fdf1e7; color: #9a4a00; }
.p-judicial { background: #eef1fd; color: #2b3f9e; }
.p-institucional { background: #edf7ef; color: #1f6b33; }
.p-prensa { background: #f4effc; color: #5b2a9e; }
.p-alerta { background: #fdecec; color: #a11d1d; }
.mi-sintesis { color: #3a3a3c; font-size: 0.93rem; }
.mi-nota { border-left: 3px solid #c7c7cc; padding-left: 0.7rem; color: #48484a; font-size: 0.85rem; margin-top: 0.4rem; }
.dic-HABILITADO { color: #1f6b33; } .dic-CONDICIONADO { color: #9a6400; }
.dic-NO { color: #a11d1d; } .dic-EN { color: #9a6400; } .dic-DIAGNÓSTICO { color: #6e6e73; }
.stButton > button, .stDownloadButton > button { border-radius: 999px; padding: 0.35rem 1.1rem; font-weight: 600; }
</style>
"""


def pastilla(texto: str, clase: str = "") -> str:
    return f'<span class="mi-pastilla {clase}">{texto}</span>'
