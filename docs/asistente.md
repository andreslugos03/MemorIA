# El asistente de consulta

El asistente es el prototipo conversacional previsto en el capítulo 8 de la tesis. No busca reemplazar la consulta a las fuentes ni la conversación con sobrevivientes. Facilita el acceso pedagógico a un cuerpo documental amplio y enseña a tratar la respuesta de la máquina como lo que es, una fuente con fecha, con productor y con intereses, que puede y debe contrastarse con otras.

Su punto de partida es una distinción. Citar un documento no equivale a conservar la voz de quien habla en él. Por eso los cinco requisitos traducen tres propiedades del archivo (polifonía, temporalidad y autoría) en comportamiento del sistema.

## Cómo responde

1. **Recupera** con BM25 los fragmentos públicos más pertinentes. Excluye siempre las fuentes restringidas y embargadas, y los testimonios sin consentimiento para procesamiento con inteligencia artificial.
2. **Se abstiene** cuando ningún fragmento supera el umbral de pertinencia (`puntaje_minimo_asistente` en `proyecto.json`) y sugiere qué tipo de fuente podría contener la respuesta.
3. **Revisa lo que saldrá** con la compuerta de contenido cuando el modelo es externo.
4. **Pide la síntesis** al modelo con la instrucción del protocolo (Anexo E) y un formato que exige citar cada oración.
5. **Posprocesa** la síntesis oración por oración. Valida cada cita contra los fragmentos entregados, reserva los nombres de víctimas cuando la consulta no los pide y pone entre comillas latinas toda expresión del léxico regional.
6. **Compone** la respuesta con los documentos primero, las discrepancias, el léxico con su atribución y la síntesis al final.

## Requisito 1. Procedencia de cada afirmación

Cada oración de la síntesis se convierte en una `Afirmacion` con sus citas válidas y una ficha de `Procedencia` por cita (documento, título, tipo de fuente, fecha, municipio y autoría). Una cita a un fragmento que el modelo no recibió se marca como no verificable, y una oración sin cita lleva el aviso correspondiente. El sistema muestra esos avisos en lugar de ocultar la oración, porque la lectura crítica necesita ver también lo que la máquina afirma sin respaldo.

## Requisito 2. Léxico regional atribuido

El léxico vive en `corpus/lexico.csv` con las columnas `termino`, `variantes`, `hablante`, `epoca`, `categoria`, `estigmatizante` y `nota`. El asistente busca cada término y sus variantes en los fragmentos recuperados y en la síntesis. En la síntesis toda aparición queda entre comillas latinas, y la respuesta presenta cada expresión con quién la usaba, en qué época y la nota ética que aprobaron las comunidades. Un término estigmatizante nunca queda como descripción propia del sistema.

## Requisito 3. Discrepancias y abstención

Los documentos del corpus pueden anotar hechos con un identificador común y los campos `fecha`, `lugar`, `victimas` y `responsable`. Cuando una consulta recupera un hecho, el asistente compara esas anotaciones en todas las fuentes públicas que lo mencionan, recuperadas o no. Dos valores son compatibles cuando uno precisa al otro (1991 y 1991-03) y discrepantes cuando no (1991-03 y 1991-04, o cuatro y cinco víctimas). Cada discrepancia se muestra con el valor, el tipo de fuente y la fecha de cada versión, sin elegir una de ellas.

## Requisito 4. El documento primero

La consola (`memoria consultar`) imprime primero la sección DOCUMENTOS con el texto completo de cada fragmento y su ficha, y al final la SÍNTESIS como lectura secundaria. La interfaz web reserva la columna principal para los documentos y la lateral para discrepancias, léxico y síntesis.

## Requisito 5. Correcciones comunitarias

El registro `correcciones/correcciones.jsonl` admite propuestas sobre un documento, un fragmento, una entrada del léxico o una respuesta. Cada propuesta exige una autoría colectiva (organización, colectivo o comunidad) y queda con fecha en tiempo universal coordinado. El panel acepta o rechaza cada propuesta con una nueva entrada, y la historia completa se conserva.

Cada línea incluye el resumen SHA-256 de la anterior. `memoria corregir proyecto verificar` recalcula la cadena y señala cualquier alteración posterior. Las correcciones aceptadas tienen efecto inmediato. Las de léxico cambian el hablante, la época, la categoría o la nota vigentes, y las de documentos o fragmentos aparecen junto al documento como notas comunitarias.

```bash
memoria corregir proyecto proponer --autoria "Asociación de Víctimas X" --objeto-tipo lexico \
    --objeto-id "Los del Puente" --categoria lexico --campo hablante \
    --texto "vendedoras y vecinos del puerto" --justificacion "Memoria del mercado"
memoria corregir proyecto resolver CORR-0001 --estado aceptada --autoria "Panel de validación"
memoria corregir proyecto verificar
```

## Usar un modelo real

El asistente usa por defecto el modelo simulado. Para usar un modelo de `sistemas.json` basta indicar su nombre.

```bash
memoria consultar proyecto "¿Qué ocurrió en Puerto Arenal en 1991?" --sistema ollama-local
```

Recomendamos un modelo de pesos abiertos en infraestructura controlada, de modo que ningún testimonio salga hacia servicios de terceros. Antes de abrir el asistente al público, ese modelo debe obtener un dictamen favorable con el Auditor, con la misma versión y la misma configuración.
