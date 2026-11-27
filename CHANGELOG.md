# Bitácora de versiones

## 0.5.0 · 2026-11-27

* Interfaz web rediseñada con el lenguaje visual de macOS e iOS. Barra lateral translúcida con secciones e íconos en teselas de color, títulos grandes, tarjetas, listas agrupadas, control segmentado, interruptores, píldoras de estado, campo de búsqueda amplio, tablas sin líneas verticales y anillo de progreso del recorrido de auditoría.
* Tema empaquetado (`memoria/app/tema_apple.toml`) con colores del sistema en variantes clara y oscura, que sigue la preferencia del sistema operativo. `memoria app` lo aplica y `.streamlit/config.toml` lo aplica al abrir la app desde la raíz del repositorio.
* Íconos propios trazados en SVG. La interfaz no usa fuentes, logotipos ni recursos de Apple.
* Corrección. Dos expresiones sueltas del código hacían que Streamlit imprimiera la lista de documentos y la descripción del índice en todas las páginas. Una prueba nueva detecta cualquier salida de ese tipo.
* Pruebas de integridad del estilo (llaves balanceadas, un ícono por sección) y del tema.

## 0.4.0 · 2026-11-26

Primera versión pública en GitHub, reconstruida desde el protocolo v1.0 y el kit de cálculo `audit_metrics.py` v1.0.

* Auditor completo. Ejecución en condiciones A y B, compuertas éticas por metadatos y por contenido, hojas ciegas con clave en custodia, validación, conciliación con alfa preliminar, descegamiento, veintiún indicadores, fiabilidad, efecto correctivo y dictamen de la Tabla 10.
* El dictamen distingue además los casos en suspenso (fiabilidad insuficiente) y provisionales (indicadores sin datos o alfa no calculable).
* Asistente de consulta con los cinco requisitos del capítulo 8 de la tesis y registro encadenado de correcciones comunitarias.
* Conectores simulado, compatible con OpenAI (Ollama, LM Studio, vLLM) y Anthropic, con manejo de respuestas mal formadas, claves ausentes y reintentos.
* Lectura de CSV con punto y coma, tabulador, BOM, Windows-1252 y coma decimal.
* Interfaz web en Streamlit y orden `memoria`.
* Proyecto de demostración ficticio con 14 documentos, 36 ítems y codificadores simulados.
* Batería de pruebas automatizadas con integración continua en Python 3.10 a 3.13.

## Antecedentes

* Protocolo de auditoría situada v1.0 para pilotaje y kit `audit_metrics.py` v1.0 (septiembre de 2026).
* Prototipo local MemorIA Auditor v0.2 y v0.3 (octubre de 2026). La v0.3 corrigió once fallos hallados con 77 pruebas automatizadas, entre ellos la segunda compuerta de ocho palabras. Esta versión reimplementa esas lecciones sobre una base nueva.
