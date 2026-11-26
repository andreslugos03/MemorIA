# Ética y gobernanza de los datos

Trabajar con archivos del conflicto exige protocolos explícitos. Adoptamos el cuidado del testimonio que enseña la historia oral (Pollak, 1989; Portelli, 1991) y lo traducimos en reglas que el software hace cumplir, porque una regla que depende solo de la buena voluntad de quien opera la herramienta falla el día que alguien se equivoca.

## Lo que el repositorio nunca contiene

* Testimonios, documentos, nombres o datos de personas reales.
* Claves de acceso a servicios. Las claves viven en variables de entorno.
* Registros de ejecución, hojas de codificación o claves de cegamiento de auditorías reales.

El archivo `.gitignore` excluye por defecto las carpetas de proyectos de trabajo. El corpus real de MemorIA se aloja en infraestructura institucional de la Universidad Industrial de Santander con niveles de acceso diferenciados.

## Reglas que aplica el software

| Regla | Dónde |
|---|---|
| Las fuentes restringidas y embargadas solo se entregan a modelos que corren en infraestructura local, y solo durante la auditoría | `compuertas.niveles_permitidos` |
| Un sistema cuenta como local solo si su configuración lo declara y su dirección es localhost | `compuertas.es_local` |
| Todo texto que va a un sistema externo se compara con las fuentes no públicas y se retiene si comparte ocho palabras seguidas con alguna | `compuertas.CompuertaContenido` |
| Un ítem marcado con fuentes restringidas o embargadas nunca se envía a un sistema externo | `compuertas.CompuertaContenido.revisar` |
| Un testimonio sin consentimiento expreso para procesamiento con IA no entra a la recuperación | `recuperacion.IndiceBM25.buscar`, `corpus` |
| La interfaz pública recupera solo fuentes públicas, también cuando el modelo es local | `asistente.Asistente.responder` |
| La síntesis reserva los nombres de víctimas cuando la consulta no los pide | `asistente.Asistente.responder` |
| Los términos estigmatizantes aparecen siempre entre comillas y atribuidos a su hablante | `asistente.Asistente._entrecomillar` |
| La clave de cegamiento se guarda aparte de las hojas de codificación | `cegamiento.preparar_hojas` |
| Las correcciones comunitarias quedan en un registro de solo anexión con verificación de integridad | `asistente.correcciones` |

## Por qué la interfaz pública solo usa fuentes públicas

La corrida de demostración de octubre de 2026 mostró que un sistema local autorizado a recuperar fuentes restringidas las filtraba en sus respuestas. La demostración de este repositorio reproduce ese hallazgo. El sistema local filtra contenido restringido y atribuye un desplazamiento a un alias que solo menciona un testimonio reservado, sin decisión judicial que lo respalde. El acceso al archivo mejora la fidelidad y, al mismo tiempo, pone en riesgo el cuidado. Solo una auditoría que mide ambas dimensiones por separado podía hacerlo visible, y la consecuencia fue una decisión de arquitectura.

## Lo que el software no resuelve

Ninguna compuerta reemplaza el consentimiento informado, el aval del comité de ética institucional, el acompañamiento psicosocial de quienes codifican contenido sobre violencia extrema ni la devolución dialógica de los resultados a las organizaciones de víctimas antes de su publicación. La compuerta de ocho palabras detecta copias literales y deja pasar paráfrasis, de modo que la codificación humana de la variable de filtración sigue siendo necesaria.

## Referencias

Pollak, M. (1989). Memória, esquecimento, silêncio. *Estudos Históricos*, *2*(3).

Portelli, A. (1991). *The death of Luigi Trastulli and other stories: Form and meaning in oral history*. State University of New York Press.
