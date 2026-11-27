"""Línea de órdenes de MemorIA.

    memoria demo [carpeta]                  instala y ejecuta la demostración ficticia
    memoria ejecutar PROYECTO               aplica el banco a los sistemas (condiciones A y B)
    memoria cegar PROYECTO                  prepara hojas ciegas y la clave de cegamiento
    memoria hoja PROYECTO HOJA CODIFICADOR  crea la hoja de un codificador
    memoria validar PROYECTO                revisa códigos y rangos de las hojas codificadas
    memoria conciliar PROYECTO              compara codificadores y prepara el consenso
    memoria descegar PROYECTO               une hojas y clave en el formato del kit de cálculo
    memoria dictamen PROYECTO               calcula indicadores, fiabilidad y dictamen
    memoria metricas --datos D --salida S   kit de cálculo sobre una carpeta de CSV
    memoria consultar PROYECTO "pregunta"   asistente de consulta
    memoria corregir PROYECTO ...           correcciones comunitarias
    memoria app [PROYECTO]                  interfaz web (requiere streamlit)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

from . import VERSION_PROTOCOLO, __version__


def _proyecto(ruta: str):
    from .proyecto import Proyecto
    if not os.path.isdir(ruta):
        sys.exit(f"No existe la carpeta de proyecto {ruta}")
    return Proyecto(ruta)


def _imprimir_dictamenes(calc):
    for (m, c), d in calc["dictamenes"].items():
        print(f"  {m} · condición {c}: {d['dictamen']}. {d['detalle']}")
        for o in d["observaciones"]:
            print(f"      {o}")


def cmd_demo(a):
    from .demo import demo_completa, instalar_demo
    if a.solo_instalar:
        instalar_demo(a.carpeta, a.sobrescribir)
        print(f"Demostración instalada en {a.carpeta}")
        return
    print("Ejecutando la demostración con datos ficticios y codificadores simulados...")
    calc = demo_completa(a.carpeta, a.sobrescribir)
    print(f"Listo. Reporte en {os.path.join(a.carpeta, 'resultados', 'reporte_auditoria.md')}")
    _imprimir_dictamenes(calc)


def cmd_ejecutar(a):
    from .ejecucion import ejecutar
    p = _proyecto(a.proyecto)
    sistemas = [s.strip() for s in a.sistemas.split(",")] if a.sistemas else None
    condiciones = tuple(c.strip().upper() for c in a.condiciones.split(","))

    def progreso(i, n):
        if i == n or i % 25 == 0:
            print(f"  {i}/{n} ejecuciones", flush=True)

    filas = ejecutar(p, sistemas, condiciones, a.estabilidad, a.hilos, a.ejecutor, progreso)
    estados = {}
    for f in filas:
        estados[(f["modelo"], f["estado"])] = estados.get((f["modelo"], f["estado"]), 0) + 1
    for (m, e), n in sorted(estados.items()):
        print(f"  {m}: {n} {e}")
    for f in filas:
        if f["estado"] != "ok":
            print(f"  [{f['estado']}] {f['modelo']} {f['id_item']} {f['condicion']}: {f['detalle']}")
    print(f"Registro en {p.ruta_registro}")


def cmd_cegar(a):
    from .cegamiento import preparar_hojas
    p = _proyecto(a.proyecto)
    r = preparar_hojas(p, a.semilla)
    for k, v in r.items():
        print(f"  {k}: {v} filas")
    print(f"Hojas ciegas en {p.dir_plantillas}")
    print(f"Clave de cegamiento en {p.ruta_clave}. Entrégala a una persona ajena a la codificación.")


def cmd_hoja(a):
    from .cegamiento import HOJAS, iniciar_hoja
    p = _proyecto(a.proyecto)
    hojas = list(HOJAS) if a.hoja == "todas" else [a.hoja]
    for h in hojas:
        if h not in HOJAS:
            sys.exit(f"Hoja desconocida {h}. Opciones: {', '.join(HOJAS)}")
        print(iniciar_hoja(p, h, a.codificador))


def cmd_validar(a):
    from .cegamiento import HOJAS, hojas_codificadas, validar
    p = _proyecto(a.proyecto)
    total = 0
    for h in HOJAS:
        for cod, filas in hojas_codificadas(p, h).items():
            errores = validar(h, filas)
            total += len(errores)
            estado = "sin errores" if not errores else f"{len(errores)} errores"
            print(f"  {h} · {cod}: {estado}")
            for e in errores[:20]:
                print(f"      {e}")
    sys.exit(1 if total else 0)


def cmd_conciliar(a):
    from .cegamiento import HOJAS
    from .conciliacion import conciliar
    p = _proyecto(a.proyecto)
    for h in (list(HOJAS) if a.hoja == "todas" else [a.hoja]):
        r = conciliar(p, h, a.sobrescribir)
        print(f"{h}: {len(r['desacuerdos'])} desacuerdos entre {', '.join(r['codificadores']) or 'nadie'}")
        if r.get("aviso"):
            print(f"  {r['aviso']}")
        for al in r["alfas"]:
            print(f"  alfa {al['variable']} ({al['nivel']}): {al['alfa']} · {al['lectura']}")
        if r.get("hoja_consenso"):
            accion = "escrita" if r["consenso_escrito"] else "ya existía, no se sobrescribió"
            print(f"  hoja de consenso {accion}: {r['hoja_consenso']}")


def cmd_descegar(a):
    from .cegamiento import descegar
    p = _proyecto(a.proyecto)
    for k, v in descegar(p).items():
        print(f"  {k}: {v} filas")
    print(f"Datos para el kit de cálculo en {p.dir_datos}")


def cmd_dictamen(a):
    from .metricas import calcular, escribir_resultados
    p = _proyecto(a.proyecto)
    calc = calcular(p.dir_datos)
    escribir_resultados(calc, p.dir_resultados)
    print(f"Resultados en {p.dir_resultados}")
    _imprimir_dictamenes(calc)


def cmd_metricas(a):
    from .metricas import main
    main(["--datos", a.datos, "--salida", a.salida])


def cmd_consultar(a):
    from .asistente import Asistente
    p = _proyecto(a.proyecto)
    sistema = p.sistema(a.sistema) if a.sistema else None
    r = Asistente(p, sistema).responder(a.pregunta)
    print(json.dumps(r.como_dict(), ensure_ascii=False, indent=2) if a.json else r.a_texto())


def cmd_corregir(a):
    from .asistente.correcciones import ErrorCorreccion, RegistroCorrecciones
    p = _proyecto(a.proyecto)
    reg = RegistroCorrecciones(p.ruta_correcciones)
    try:
        if a.accion == "proponer":
            e = reg.proponer(a.autoria, a.objeto_tipo, a.objeto_id, a.categoria, a.texto, a.justificacion or "",
                             a.campo or "", a.texto_actual or "")
            print(f"Corrección {e['id']} registrada el {e['fecha_utc']}")
        elif a.accion == "resolver":
            e = reg.resolver(a.id, a.estado, a.autoria, a.motivo or "")
            print(f"Corrección {a.id} {a.estado} el {e['fecha_utc']}")
        elif a.accion == "listar":
            for c in reg.estado_actual():
                pr = c.propuesta
                print(f"{pr['id']} · {c.estado} · {pr['fecha_utc'][:10]} · {pr['autoria_colectiva']} · "
                      f"{pr['objeto']['tipo']} {pr['objeto']['id']} · {pr['texto_propuesto']}")
        else:
            ok, problemas = reg.verificar()
            print("Registro íntegro" if ok else "El registro fue alterado:")
            for x in problemas:
                print(f"  {x}")
            sys.exit(0 if ok else 1)
    except ErrorCorreccion as e:
        sys.exit(str(e))


def cmd_app(a):
    try:
        import streamlit  # noqa: F401
    except ImportError:
        sys.exit("La interfaz web requiere Python 3.11 o superior y streamlit. Instálala con: "
                 "pip install \"memoria-ia[app] @ git+https://github.com/andreslugos03/MemorIA\"")
    app = os.path.join(os.path.dirname(__file__), "app", "app.py")
    env = {**os.environ}
    if a.proyecto:
        env["MEMORIA_PROYECTO"] = os.path.abspath(a.proyecto)
    tema = os.path.join(os.path.dirname(__file__), "app", "tema_apple.toml")
    orden = [sys.executable, "-m", "streamlit", "run", app, "--server.port", str(a.puerto), "--theme.base", tema,
             "--browser.gatherUsageStats", "false"]
    sys.exit(subprocess.call(orden, env=env))


def construir_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="memoria", description="Auditoría situada de modelos de lenguaje y asistente de consulta MemorIA")
    ap.add_argument("--version", action="version", version=f"memoria {__version__} · protocolo v{VERSION_PROTOCOLO}")
    sub = ap.add_subparsers(dest="orden", required=True)

    s = sub.add_parser("demo", help="instala y ejecuta la demostración con datos ficticios")
    s.add_argument("carpeta", nargs="?", default="memoria_demo")
    s.add_argument("--sobrescribir", action="store_true")
    s.add_argument("--solo-instalar", action="store_true", help="copia la demostración sin ejecutarla")
    s.set_defaults(fn=cmd_demo)

    s = sub.add_parser("ejecutar", help="aplica el banco de ítems a los sistemas")
    s.add_argument("proyecto")
    s.add_argument("--sistemas", help="nombres separados por coma (por defecto, todos)")
    s.add_argument("--condiciones", default="A,B")
    s.add_argument("--estabilidad", action="store_true", help="agrega la submuestra de estabilidad a temperatura 0,7")
    s.add_argument("--hilos", type=int, default=1)
    s.add_argument("--ejecutor", default=os.environ.get("USER", ""))
    s.set_defaults(fn=cmd_ejecutar)

    s = sub.add_parser("cegar", help="prepara hojas ciegas y la clave de cegamiento")
    s.add_argument("proyecto")
    s.add_argument("--semilla", type=int, default=None, help="solo para pruebas reproducibles")
    s.set_defaults(fn=cmd_cegar)

    s = sub.add_parser("hoja", help="crea la hoja de un codificador a partir de la plantilla ciega")
    s.add_argument("proyecto")
    s.add_argument("hoja", help="nombre de la hoja o «todas»")
    s.add_argument("codificador")
    s.set_defaults(fn=cmd_hoja)

    s = sub.add_parser("validar", help="revisa las hojas codificadas")
    s.add_argument("proyecto")
    s.set_defaults(fn=cmd_validar)

    s = sub.add_parser("conciliar", help="compara codificadores y prepara la hoja de consenso")
    s.add_argument("proyecto")
    s.add_argument("--hoja", default="todas")
    s.add_argument("--sobrescribir", action="store_true")
    s.set_defaults(fn=cmd_conciliar)

    s = sub.add_parser("descegar", help="une las hojas codificadas con la clave")
    s.add_argument("proyecto")
    s.set_defaults(fn=cmd_descegar)

    s = sub.add_parser("dictamen", help="calcula indicadores, fiabilidad y dictamen del proyecto")
    s.add_argument("proyecto")
    s.set_defaults(fn=cmd_dictamen)

    s = sub.add_parser("metricas", help="kit de cálculo sobre una carpeta de CSV (compatible con audit_metrics v1.0)")
    s.add_argument("--datos", default="plantillas")
    s.add_argument("--salida", default="resultados")
    s.set_defaults(fn=cmd_metricas)

    s = sub.add_parser("consultar", help="pregunta al asistente de consulta")
    s.add_argument("proyecto")
    s.add_argument("pregunta")
    s.add_argument("--sistema", help="sistema de sistemas.json (por defecto, el simulado)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_consultar)

    s = sub.add_parser("corregir", help="propone, resuelve, lista o verifica correcciones comunitarias")
    s.add_argument("proyecto")
    acc = s.add_subparsers(dest="accion", required=True)
    pr = acc.add_parser("proponer")
    pr.add_argument("--autoria", required=True, help="organización, colectivo o comunidad que propone")
    pr.add_argument("--objeto-tipo", required=True, choices=("documento", "fragmento", "lexico", "respuesta"))
    pr.add_argument("--objeto-id", required=True)
    pr.add_argument("--categoria", required=True, choices=("lexico", "hecho", "atribucion", "cuidado", "procedencia", "otra"))
    pr.add_argument("--texto", required=True, help="texto propuesto")
    pr.add_argument("--campo", help="para el léxico: hablante, epoca, nota o categoria")
    pr.add_argument("--texto-actual")
    pr.add_argument("--justificacion")
    rs = acc.add_parser("resolver")
    rs.add_argument("id")
    rs.add_argument("--estado", required=True, choices=("aceptada", "rechazada"))
    rs.add_argument("--autoria", required=True)
    rs.add_argument("--motivo")
    acc.add_parser("listar")
    acc.add_parser("verificar")
    s.set_defaults(fn=cmd_corregir)

    s = sub.add_parser("app", help="abre la interfaz web")
    s.add_argument("proyecto", nargs="?")
    s.add_argument("--puerto", type=int, default=8501)
    s.set_defaults(fn=cmd_app)
    return ap


def main(argv=None):
    a = construir_parser().parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
