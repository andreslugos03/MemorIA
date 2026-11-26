# Cómo contribuir

Agradecemos las contribuciones de historiadores, archivistas, personas de organizaciones de víctimas, especialistas en lenguaje y desarrolladores. MemorIA es un instrumento de investigación, de modo que una buena contribución puede ser tanto una corrección de código como una objeción metodológica.

## Antes de empezar

* Nunca subas testimonios, documentos ni nombres de personas reales, tampoco en un *issue*, en una prueba o en un ejemplo. Los datos de demostración son ficticios y así deben seguir.
* Si encuentras un riesgo para personas reales, sigue [SEGURIDAD.md](SEGURIDAD.md) y escríbenos en privado.
* Los umbrales y las reglas de dictamen pertenecen al protocolo. Un cambio en ellos requiere una propuesta metodológica razonada y su registro en la bitácora de versiones del protocolo. Los umbrales de fallo crítico (C2 y C4) no se pueden relajar.

## Flujo de trabajo

```bash
git clone https://github.com/andreslugos03/MemorIA
cd MemorIA
pip install -e ".[app]"
python -m unittest discover -s tests
```

1. Abre un *issue* que describa el problema o la propuesta.
2. Trabaja en una rama propia y agrega pruebas que cubran el cambio.
3. Mantén el núcleo sin dependencias externas. Solo la interfaz web usa Streamlit.
4. Abre una solicitud de cambios que explique qué cambia, por qué y cómo se probó.

## Estilo

* El código, los nombres y la documentación están en español.
* Las funciones públicas llevan una descripción breve de su propósito.
* Una regla ética que el software hace cumplir debe tener al menos una prueba que falle si la regla se rompe.
