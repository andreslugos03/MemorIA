# MemorIA

**Auditoría situada de modelos de lenguaje y asistente de consulta para archivos testimoniales del conflicto armado colombiano**

[![Pruebas](https://github.com/andreslugos03/MemorIA/actions/workflows/pruebas.yml/badge.svg)](https://github.com/andreslugos03/MemorIA/actions/workflows/pruebas.yml)
![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)
![Licencia](https://img.shields.io/badge/licencia-AGPL--3.0-green)
![Estado](https://img.shields.io/badge/estado-prototipo%20doctoral-orange)

MemorIA es el prototipo de software del proyecto doctoral *MemorIA. Análisis con modelos de lenguaje de gran escala de los archivos del conflicto armado en Santander (1985-2016)*, que desarrollamos en el Doctorado en Ciencias Sociales y Humanas de la Universidad Industrial de Santander con el grupo de investigación PSORHE.

Partimos de una pregunta. Cada vez más personas leen el pasado a través de chatbots y resúmenes automáticos, y en los archivos del conflicto esa mediación tiene consecuencias. Una máquina puede aplanar el vocabulario con que una región nombró la violencia, inventar datos con aparente seguridad o exponer a las víctimas. Llamamos **epistemicidio algorítmico** a ese riesgo, y el repositorio reúne dos instrumentos para observarlo y contenerlo.

| Instrumento | Qué hace |
|---|---|
| **Auditor** | Ejecuta el protocolo de auditoría situada v1.0. Cuatro pruebas (léxica, territorial, fidelidad y cuidado), veintiún indicadores con umbral explícito, doble codificación ciega, alfa de Krippendorff y un dictamen por sistema y condición. |
| **Asistente** | Responde consultas sobre el corpus con el documento en primer plano, la procedencia de cada afirmación, el léxico regional atribuido a su hablante y su época, las discrepancias entre fuentes, la abstención declarada y un registro verificable de correcciones comunitarias. |

> **Advertencia.** Todos los datos incluidos en este repositorio son ficticios. Los municipios, las personas, los periódicos, las sentencias y los hechos de la demostración fueron inventados para probar el software. El repositorio nunca contendrá testimonios reales.

## Instalación

Requiere Python 3.10 o superior. El núcleo funciona solo con la biblioteca estándar, y la interfaz web usa Streamlit.

```bash
pip install "memoria-ia[app] @ git+https://github.com/andreslugos03/MemorIA"
```

Para trabajar sobre el código.

```bash
git clone https://github.com/andreslugos03/MemorIA
cd MemorIA
pip install -e ".[app]"
python -m unittest discover -s tests
```

## Primeros pasos con la demostración

```bash
memoria demo mi_demo            # instala el proyecto ficticio y recorre el protocolo completo
memoria app mi_demo             # abre la interfaz web en http://localhost:8501
memoria consultar mi_demo "¿Qué ocurrió en Puerto Arenal en 1991?"
```

La demostración aplica un banco de 36 ítems a dos sistemas simulados, uno local con acceso a fuentes restringidas y otro externo que solo recibe fuentes públicas. Produce 176 ejecuciones, de las cuales las compuertas éticas retienen 6 antes de que salgan hacia el sistema externo. Codificadores simulados reemplazan a las personas solo en esta demostración. El reporte queda en `mi_demo/resultados/reporte_auditoria.md`.

Lo que muestra la demostración, con datos ficticios.

* En la condición A los dos sistemas responden sin el archivo y alucinan en 0,889 de sus afirmaciones verificables. Con recuperación sobre el corpus (condición B) esa tasa cae a 0,000.
* El sistema local con acceso a fuentes restringidas las filtra en sus respuestas (C2 = 0,571) y atribuye responsabilidad a un alias sin soporte judicial (C4 = 0,667). Ambos son fallos críticos y el dictamen es NO HABILITADO.
* El sistema externo no filtra porque la compuerta nunca le entrega lo restringido. Sigue fuera de la interfaz pública por incumplimientos léxicos, territoriales, de abstención y de lenguaje revictimizante.

Esa es la lección de diseño que ya encontramos en la corrida de demostración de octubre de 2026. El recurso que mejora la fidelidad, el acceso al archivo, es el mismo que pone en riesgo el cuidado. Por eso el asistente público de MemorIA recupera solo fuentes públicas, incluso cuando el modelo corre en un computador local.

## Interfaz

La interfaz web sigue el lenguaje visual de macOS e iOS. Tiene una barra lateral translúcida con íconos en teselas de color, títulos grandes, tarjetas, listas agrupadas, controles segmentados, colores del sistema y tipografía San Francisco en los equipos que la tienen. Cambia sola entre modo claro y modo oscuro según la preferencia del sistema operativo. No incluye fuentes, logotipos ni recursos de Apple, y en otros sistemas usa Helvetica Neue, Segoe UI o Roboto.

![Inicio del proyecto en modo claro](docs/capturas/inicio-claro.png)

| Asistente | Dictamen en modo oscuro |
|---|---|
| ![Asistente con los documentos en primer plano](docs/capturas/asistente-claro.png) | ![Perfil de indicadores en modo oscuro](docs/capturas/dictamen-oscuro.png) |

`memoria app` aplica el tema de forma automática. Para abrir la app directamente con Streamlit desde la raíz del repositorio basta `streamlit run memoria/app/app.py`, porque `.streamlit/config.toml` apunta al mismo tema.

## Recorrido de una auditoría real

```bash
memoria ejecutar proyecto                    # aplica el banco en las condiciones A y B
memoria cegar proyecto                       # hojas ciegas y clave de cegamiento
memoria hoja proyecto todas cod1             # hojas de cada codificador
memoria hoja proyecto todas cod2
#   ... codificación humana en la app o en una hoja de cálculo ...
memoria validar proyecto                     # revisa códigos y rangos
memoria conciliar proyecto                   # alfa preliminar, desacuerdos y hoja de consenso
memoria descegar proyecto                    # une hojas y clave
memoria dictamen proyecto                    # indicadores, fiabilidad, efecto correctivo y dictamen
```

La estructura de un proyecto, los formatos de cada archivo y la configuración de los sistemas están en [docs/arquitectura.md](docs/arquitectura.md). El protocolo con sus fórmulas, umbrales y reglas de dictamen está en [docs/protocolo.md](docs/protocolo.md).

### Sistemas que se pueden auditar

| Proveedor | Uso |
|---|---|
| `simulado` | Modelo determinista sin red, para demostraciones y pruebas |
| `openai_compatible` | Ollama, LM Studio, vLLM, llama.cpp, OpenAI y cualquier servicio con la ruta `/chat/completions` |
| `anthropic` | API de mensajes de Anthropic |

Un sistema cuenta como local cuando su configuración lo declara y además su dirección es `localhost`. Solo un sistema local recibe fuentes restringidas o embargadas, y lo hace exclusivamente durante la auditoría. El archivo [docs/sistemas.ejemplo.json](docs/sistemas.ejemplo.json) trae configuraciones de ejemplo.

## El asistente y sus cinco requisitos

| Requisito | Implementación |
|---|---|
| 1. Cada afirmación muestra su documento, su tipo de fuente y su fecha | La síntesis se divide en oraciones, cada cita se valida contra los fragmentos entregados y se convierte en una ficha de procedencia. Una cita a un fragmento no entregado o una oración sin cita quedan marcadas. |
| 2. Las expresiones del léxico regional van entre comillas, con su hablante y su época | El léxico validado se busca en los fragmentos y en la síntesis. Toda aparición queda entre comillas latinas y cada expresión se presenta con hablante, época y nota ética. |
| 3. El asistente señala las discrepancias y declara cuándo no sabe | Los hechos anotados en el corpus se comparan entre todas las fuentes públicas. Sin respaldo suficiente el asistente se abstiene y sugiere qué tipo de fuente consultar. |
| 4. El documento va primero y la síntesis después | La consola y la interfaz web muestran primero los documentos completos con su ficha y dejan la síntesis como lectura secundaria. |
| 5. Las comunidades proponen correcciones con fecha y autoría colectiva | Un registro JSONL de solo anexión encadena cada entrada con el resumen SHA-256 de la anterior. Las correcciones aceptadas por el panel modifican el léxico vigente o acompañan al documento como nota comunitaria. |

El detalle está en [docs/asistente.md](docs/asistente.md).

## Cuidado de los datos

* La fracción restringida y embargada del corpus nunca se envía a servicios comerciales. Dos compuertas lo impiden, una por metadatos y otra por contenido (ocho palabras seguidas en común con una fuente no pública).
* Un testimonio sin consentimiento expreso para procesamiento con inteligencia artificial no entra a la recuperación, y uno sin registro de consentimiento se trata como no consentido.
* La síntesis reserva los nombres de víctimas cuando la consulta no los pide.
* La clave de cegamiento se guarda aparte para que la custodie una persona ajena a la codificación.

El marco completo está en [docs/etica-y-gobernanza.md](docs/etica-y-gobernanza.md). Si encuentras un riesgo para personas reales, escríbenos en privado según [SEGURIDAD.md](SEGURIDAD.md) y no abras un *issue* público.

## Pruebas

```bash
python -m unittest discover -s tests
```

La batería reproduce el ejemplo publicado por Krippendorff (2011) para el alfa (0,743 en nivel nominal y 0,849 en nivel de intervalo), calcula a mano cada uno de los veintiún indicadores, prueba las reglas de dictamen, las compuertas éticas, los conectores frente a respuestas mal formadas y claves ausentes, el cegamiento, la conciliación, los cinco requisitos del asistente, la detección de alteraciones en el registro de correcciones y el renderizado de todas las páginas de la interfaz. GitHub Actions la ejecuta en Python 3.10 a 3.13 en cada cambio.

## Límites que declaramos

* La auditoría de caja negra observa conducta y no mecanismos. Su resultado vale para una versión concreta de un modelo, con una configuración y una fecha.
* La prueba territorial mide correspondencia con lo documentado y no con la totalidad de lo ocurrido, de modo que hereda los silencios del archivo.
* Los umbrales son iniciales y ganarán respaldo empírico tras el pilotaje.
* Las citas entre corchetes delatan la condición B ante los codificadores, porque la prueba de fidelidad necesita verlas.
* El modelo simulado y los codificadores simulados solo sirven para demostrar el flujo. Sus cifras no describen a ningún modelo existente.
* La recuperación es léxica (BM25). Una recuperación semántica queda como trabajo futuro y deberá auditarse con el mismo protocolo.

## Cómo citar

Correa Lugos, A. D. (2026). *MemorIA. Auditoría situada de modelos de lenguaje y asistente de consulta para archivos testimoniales del conflicto armado* (versión 0.5.0) [Software]. Universidad Industrial de Santander. https://github.com/andreslugos03/MemorIA

El archivo [CITATION.cff](CITATION.cff) permite citarlo desde GitHub.

## Licencia

El código se distribuye bajo la [GNU Affero General Public License v3.0](LICENSE). Quien ofrezca una versión modificada como servicio en red debe publicar su código. Elegimos esa licencia porque la memoria del conflicto es un bien común y las herramientas que la median también deben serlo. La documentación y los datos ficticios de demostración se distribuyen bajo [Creative Commons Atribución 4.0](https://creativecommons.org/licenses/by/4.0/deed.es).

## English summary

MemorIA is the research software of a doctoral project at Universidad Industrial de Santander (Colombia). It contains two tools. The **Auditor** runs a situated audit protocol for large language models that mediate testimonial archives of the Colombian armed conflict, with four tests (lexical, territorial, fidelity and care), twenty-one indicators with explicit thresholds, blind double coding, Krippendorff's alpha and a verdict per system and condition. It deliberately refuses a composite score. The **Assistant** answers questions over a curated corpus with documents first, per-claim provenance, regional vocabulary attributed to its speakers and era, source disagreements, explicit abstention and a tamper-evident log of community corrections. Restricted testimony never leaves the local machine. All bundled data are fictitious. Run `memoria demo my_demo` to see the full pipeline.

---

Andrés David Correa Lugos · Doctorado en Ciencias Sociales y Humanas, Universidad Industrial de Santander · Grupo PSORHE · [ORCID 0000-0002-6477-8001](https://orcid.org/0000-0002-6477-8001)
