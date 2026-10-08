# Validación V2

La aplicación se valida en dos capas: pytest verifica cálculos y estado de sesión con AppTest; Chromium comprueba carga real, renderizado y geometría responsive. Las capturas utilizan exclusivamente el ejemplo ficticio incluido en el repositorio.

## Comprobación automatizada

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
```

Se conservan las 18 pruebas V1. Las pruebas V2 cubren hojas independientes (incluidas vacías), conservación del original e historial entre cambios de hoja, evidencia de claves, concatenación, cuatro tipos de JOIN, cardinalidad, claves compuestas y nulas, límite previo a explosiones de filas, agregación y datasets derivados, selección de gráficos, método de atípicos, exportación multitabla y aprobación adicional de operaciones con riesgo.

## Comprobación visual reproducible

Opcional para desarrollo; no agregar Chromium ni Playwright al despliegue Streamlit.

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
# Con Chromium instalado en /usr/bin/chromium y el servidor iniciado en 8502:
.venv/bin/python scripts/visual_check.py --url http://127.0.0.1:8502 --output /tmp/dataclean-visual
```

El script verifica ausencia de desbordamiento horizontal a 1440, 768 y 390 px, ancho de gráficos en móvil, cambio de tema sin pérdida de datos, color de títulos Plotly y aislamiento del tema entre sesiones. Genera capturas y `results.json`. También se comprobó en Chromium la importación real de un XLSX de dos hojas junto con un CSV, el selector de tablas y el análisis de relaciones.

Las capturas de `screenshots/` muestran el resultado revisado. Las pruebas de navegador no equivalen a una auditoría de accesibilidad ni a validación de todos los navegadores. Los límites del alojamiento gratuito requieren probar datasets reales representativos después del despliegue.

## Resultado de esta entrega

- **38 pruebas pytest pasaron**, incluidas las 18 originales.
- `pip check`: no hay requisitos incompatibles.
- Servidor iniciado con `streamlit run app.py`; salud responde `ok`.
- Script de Chromium completó todas sus aserciones en modo claro y oscuro.
- Geometría registrada: sin desbordamiento horizontal en 1440, 768 y 390 px; los gráficos de 390 px ocupan 358 px dentro del área de contenido.
- Importación real de dos hojas XLSX más un CSV confirmada en navegador.
- Preferencia de tema preservada sin pérdida de las ocho filas del ejemplo; una sesión paralela mantiene un tema diferente.

[Dashboard claro](screenshots/dashboard-light.png) · [Dashboard oscuro](screenshots/dashboard-dark.png) · [Visualizaciones](screenshots/visualizations-dark.png) · [Móvil](screenshots/visualizations-mobile.png)
