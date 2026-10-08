# DataClean AI — by Sánchez Gastón

Aplicación gratuita en español para explorar, revisar y limpiar archivos CSV, XLSX y XLS. Versión 1.0. Utiliza estadísticas y reglas transparentes; no utiliza APIs pagas ni modelos remotos.

## Instalación y uso

Requiere Python 3.11 o 3.12 (validado con Python 3.12).

```bash
cd dataclean-ai
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

En Windows, activar con `.venv\Scripts\activate`. La interfaz muestra la dirección de acceso cuando se ejecuta en tu propia computadora.

1. En **Inicio e importación**, cargar CSV o Excel o utilizar el ejemplo ficticio. Seleccionar hoja, codificación, separador, decimal y miles antes de importar. Las fechas se convierten explícitamente en Limpieza para conservar valores inválidos hasta que se apruebe su conversión.
2. Explorar **Resumen** y **Calidad**. Indicar claves y rangos de negocio si se conocen.
3. En **Limpieza y normalización**, seleccionar operación y columnas, preparar vista previa, revisar advertencias y marcar la aprobación antes de aplicar. Deshacer revierte la última operación; restablecer recupera el original y vacía el historial.
4. Explorar hallazgos y construir gráficos con medidas, agregaciones y filtros.
5. Comparar original y resultado, descargar CSV, XLSX, informe HTML, estadísticas e historial JSON. Los gráficos se descargan como HTML interactivo autónomo.

La normalización relacional produce propuestas explicativas basadas en claves y una dependencia de negocio indicada por vez; nunca separa tablas automáticamente. Una dependencia observada no prueba que sea válida para todos los datos futuros. La suma de identificadores o medidas no aditivas carece de significado de negocio.

## Índice de calidad

`100 × (0,50 × completitud + 0,30 × unicidad + 0,20 × consistencia)`.

- Completitud = 1 − celdas nulas o textos vacíos / total de celdas.
- Unicidad = 1 − duplicados completos posteriores a la primera aparición / filas.
- Consistencia = 1 − celdas con espacios extremos, variantes de categorías, fechas inválidas o valores fuera del rango indicado / celdas. Cada celda se cuenta una sola vez aunque tenga varios problemas.

Los atípicos, columnas constantes y sospechas de tipo se muestran para revisión, pero no penalizan el índice. Los duplicados por claves se informan aparte. Los rangos definidos en Calidad afectan su índice en esa sección; comparación e informe usan el índice base, sin rangos. Las fechas inferidas por nombre usan día/mes/año para la detección. El índice es **orientativo y no una certificación**. IQR identifica valores fuera de Q1 − 1,5 × IQR y Q3 + 1,5 × IQR. Z-score marca desviaciones superiores a 3 y requiere evaluar la distribución antes de interpretarlas.

## Privacidad y límites

- Archivos procesados en memoria; sin guardado permanente, ejecución de contenido subido ni telemetría de Streamlit.
- Máximo 20 MB, dos millones de celdas y 100 MB de contenido descomprimido XLSX. Las copias e historial consumen memoria adicional. Para grandes datasets usar herramientas específicas de procesamiento por lotes.
- El original permanece separado. Importar otro archivo reemplaza la sesión de trabajo anterior.
- CSV exportado usa por defecto punto y coma, coma decimal y UTF-8 con BOM para Excel en español.
- Se neutralizan textos y encabezados potencialmente interpretables como fórmulas en CSV/XLSX; se antepone un apóstrofo. Este cambio solo afecta la exportación.
- No subir datos sensibles a aplicaciones públicas. El proveedor de alojamiento gestiona su propia infraestructura y registros.
- El tema se conserva durante la sesión y adapta gráficos. La detección automática del tema y persistencia entre sesiones quedan como mejora futura; controles internos de Streamlit pueden conservar parte de su tema nativo.
- Pandas puede desambiguar encabezados repetidos al importar (por ejemplo `nombre.1`); revisar encabezados antes de estandarizarlos.
- Reemplazo exacto de categorías implementado para textos. Fechas inválidas y números no convertibles pasan a nulos, previa aprobación. Las sugerencias geográficas son heurísticas; no hay mapas ni inferencias causales.
- Vista previa limitada a 25 filas; el contador corresponde al dataset completo. Filtrado de gráficos ofrece hasta 1000 valores distintos.
- Excel de salida elimina zona horaria y no conserva formatos, macros ni fórmulas del archivo original. No se generan gráficos PNG/PDF; el HTML interactivo es la alternativa disponible.

## Pruebas

```bash
python -m pytest -q
```

Incluyen procesamiento y pruebas de interfaz con `streamlit.testing.v1.AppTest`: navegación, aprobación obligatoria, aplicar, deshacer y cambio de tema sin perder el dataset. El ejemplo `data/ventas_ejemplo.csv` contiene únicamente datos ficticios.

## Despliegue gratuito en Streamlit Community Cloud

1. Incorporar estos archivos a la rama principal de `gaston3461/dataclean-ai` en GitHub.
2. Entrar en https://share.streamlit.io/ con GitHub y crear una aplicación.
3. Elegir repositorio `gaston3461/dataclean-ai`, rama `main` y archivo `app.py`.
4. En opciones avanzadas, seleccionar Python 3.12 y desplegar. No se requieren secretos, claves API ni servicios adicionales.
5. Probar la importación del ejemplo, limpieza y exportación desde la aplicación desplegada.

El plan gratuito tiene límites de memoria y puede suspender aplicaciones inactivas. El despliegue requiere tu cuenta de GitHub/Streamlit; no se realiza automáticamente desde este repositorio.

## Arquitectura

`app.py`: interfaz y estado de sesión. `dataclean/loading.py`: importación. `profiling.py`: perfil y estadísticas. `quality.py`: diagnóstico. `cleaning.py`: transformaciones e historial. `normalization.py`: propuestas relacionales. `insights.py`: reglas interpretables. `charts.py`: gráficos Plotly. `exporting.py`: descargas seguras. `tests/`: pruebas.
