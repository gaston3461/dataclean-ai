# DataClean AI V2: dashboard automático, múltiples tablas y consolidación validada

La aplicación ahora importa todas las hojas Excel y múltiples CSV en una sesión y conserva un original e historial independiente por tabla. Al importar genera un dashboard con gráficos puntuados según las variables reales y sus propiedades; el usuario puede filtrar o pasar al editor manual existente.

Agrega Relaciones y consolidación con evidencia de nombres, tipos, coincidencias y unicidad. Concatenaciones y JOIN se preparan como vista previa; Pandas valida cardinalidad y la aplicación estima la expansión antes de materializar resultados. Claves nulas nunca se emparejan, se admiten claves compuestas y agregaciones previas, y operaciones con riesgo necesitan confirmación adicional. Los resultados crean nuevos datasets sin cambiar las fuentes.

Rediseña el dashboard con CSS, componentes HTML, tablas interactivas y Plotly adaptados a modo claro/oscuro y móvil. El diagnóstico de atípicos selecciona IQR o Z-score con reglas documentadas y excluye identificadores. Las exportaciones incluyen libros multitabla, historial y resumen de calidad.

## Validación

- 38 pruebas pytest pasan, conservando las 18 V1.
- AppTest verifica independencia entre hojas, aprobación y confirmación adicional de riesgos, y bloqueo de vistas previas obsoletas.
- Chromium verifica temas, conservación de datos, aislamiento entre sesiones y geometría a 1440, 768 y 390 px; se incluye script reproducible y capturas en docs/.
- Importación real de Excel de dos hojas más CSV probada en navegador.
- pip check sin incompatibilidades; Streamlit inicia y salud responde ok.

## Límites de revisión

La inferencia de roles, normalidad y relaciones es heurística, no certificación ni evidencia causal. La selección genera menos de cuatro gráficos si faltan datos válidos. Tablas interactivas limitadas a 2000 filas, dispersión/boxplots a 5000 puntos; descargas y cálculos usan el dataset filtrado completo. Consolidaciones limitadas a 200.000 filas y dos millones de celdas. Mantiene Python 3.12/Streamlit Community Cloud, sin servicios pagos ni credenciales nuevas. El despliegue público queda a cargo del propietario.
