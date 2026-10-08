# DataClean AI — by Sánchez Gastón

Aplicación gratuita en español para explorar, revisar y limpiar archivos CSV, XLSX y XLS. Versión 2.0. Utiliza estadísticas y reglas transparentes; no utiliza APIs pagas ni modelos remotos.

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
- El original permanece separado. Importar archivos agrega tablas a la sesión; el selector permite elegir el dataset activo.
- CSV exportado usa por defecto punto y coma, coma decimal y UTF-8 con BOM para Excel en español.
- Se neutralizan textos y encabezados potencialmente interpretables como fórmulas en CSV/XLSX; se antepone un apóstrofo. Este cambio solo afecta la exportación.
- No subir datos sensibles a aplicaciones públicas. El proveedor de alojamiento gestiona su propia infraestructura y registros.
- El tema se conserva durante la sesión y mediante la URL; adapta controles, tablas y gráficos. La detección automática del tema del navegador queda como mejora futura.
- Pandas puede desambiguar encabezados repetidos al importar (por ejemplo `nombre.1`); revisar encabezados antes de estandarizarlos.
- Reemplazo exacto de categorías implementado para textos. Fechas inválidas y números no convertibles pasan a nulos, previa aprobación. Las sugerencias geográficas son heurísticas; no hay mapas ni inferencias causales.
- Vista previa limitada a 25 filas; el contador corresponde al dataset completo. El editor manual de gráficos ofrece hasta 1000 valores distintos; el dashboard incluye categorías con hasta 1000 valores distintos.
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

## Actualización V2

DataClean AI V2 conserva las nueve secciones originales y agrega **Dashboard automático** y **Relaciones y consolidación**. El dashboard también aparece directamente en Inicio tras importar datos.

### Tablas independientes

Seleccionar uno o varios CSV/Excel en el cargador y presionar **Importar archivos**. Excel se importa completo; cada hoja (incluidas hojas vacías) tiene su propio original, limpieza, historial, deshacer y restablecimiento. Los archivos nuevos se agregan a la sesión sin borrar tablas existentes. Elegir **Dataset activo** en el menú lateral para cambiar entre hojas, archivos o consolidados. El panel **Tablas de la sesión y calidad por hoja** muestra filas, columnas, tipos, faltantes, duplicados y estado orientativo.

La importación es atómica: si un archivo falla o supera los límites no se incorporan parcialmente las tablas del lote. Límites: 40 datasets, cuatro millones de celdas importadas por sesión y dos millones por libro; la memoria de originales, historiales, gráficos y derivados se suma a estos datos. Una hoja vacía recibe índice 0 por falta de evidencia evaluable.

### Dashboard y gráficos automáticos

El motor infiere roles sin modificar los datos: fechas reconocidas, medidas numéricas, categorías, geografías e identificadores. Fechas textuales requieren nombre de fecha y al menos 80% de valores no nulos convertibles. Usa día primero; revisá fechas ambiguas. Geografías se muestran como categorías, sin geocodificación externa.

Puntúa candidatos con criterios transparentes: temporales 90 + hasta 5 por cobertura; barras 85 + 5 para importes/cantidades; histogramas 65 + hasta 10 por cobertura; frecuencia 68 + hasta 10 por cobertura; boxplots 79; correlación 81; dispersión 77 + 10 × |r|. Incluye razones, pregunta sugerida y hallazgo calculado por gráfico. No son probabilidades ni pruebas de significancia.

Selecciona seis gráficos por defecto (configurable a cuatro u ocho), con hasta dos por familia para favorecer diversidad. Si no hay evidencia suficiente, genera menos. Barras muestran hasta 15 categorías; boxplots hasta 12. Dispersión y boxplots se limitan a 5000 puntos reproducibles; sus conclusiones usan todos los registros filtrados. Matrices incluyen hasta 12 medidas, al menos cinco pares válidos; dispersión requiere ocho pares y |Pearson r| ≥ 0,35. Se excluyen identificadores y posibles categorías numéricas codificadas. No se trazan líneas sobre categorías sin orden válido. Las tendencias usan agregación diaria o mensual según amplitud del período: suma para cantidades/importes, media para otras medidas. No infieren causalidad.

Usar **Filtros y variables detectadas** para explorar categorías y fechas. Los KPIs generales usan el dataset completo; gráficos, conclusiones e insights usan el filtro activo. La pestaña **Editor manual** conserva las visualizaciones configurables V1.

### Relaciones y consolidación

1. Importar al menos dos tablas y abrir **Relaciones y consolidación**.
2. Presionar **Analizar relaciones**. Examinar compatibilidad de tipos, similitud de nombres, coincidencias reales, porcentajes de cobertura/unicidad, nulos, duplicados y cardinalidad probable. Se reconocen ejemplos de alias como DNI/Documento, ID_Cliente/Cliente_ID y Código_Producto/CodProducto.
3. Elegir tablas, concatenación o JOIN, claves (incluidas compuestas), tipo INNER/LEFT/RIGHT/OUTER y cardinalidad que Pandas debe validar.
4. Opcionalmente agregar medidas por claves antes de unir. Solo se retienen claves y medidas elegidas en esa vista temporal; las fuentes no se alteran.
5. Preparar el resultado, revisar número estimado y real de filas, nulos, claves repetidas, filas sin coincidencia, factor de expansión y vista previa.
6. Aprobar explícitamente. Si hay riesgo, también marcar la aceptación de multiplicación/pérdida de detalle. **Crear dataset derivado** incorpora una tabla nueva y selecciona su dataset. Las fuentes y sus historiales permanecen intactos.

Los nulos y textos vacíos de claves nunca se emparejan entre sí, incluso en claves compuestas. Se conservan como registros sin coincidencia donde el JOIN lo permite o se excluyen según opción explícita. La columna `_merge` identifica `both`, `left_only` y `right_only`; se reserva ese nombre. Columnas no clave repetidas reciben sufijos `_izq`/`_der`. No se convierten automáticamente tipos de claves ni se eliminan ceros iniciales. Convertir explícitamente desde Limpieza si se necesita corregir tipos.

El estimador calcula la multiplicación de cada clave antes de materializar el JOIN. Bloquea resultados mayores de 200.000 filas o dos millones de celdas; valida cardinalidad con `merge(validate=...)` y exige que el tamaño real coincida con el previsto. Uno a muchos puede repetir atributos de la tabla padre, y muchos a muchos puede duplicar totales: mantener un modelo relacional o agregar previamente suele ser preferible. Las relaciones observadas no demuestran equivalencia semántica, reglas permanentes ni integridad referencial. El análisis automático explora hasta 60 columnas por tabla y muestra las 30 candidatas mejor puntuadas. Claves compuestas se seleccionan manualmente.

### Valores atípicos automáticos

El diagnóstico permite **Automático**, **IQR** o **Z-score**, con umbrales configurables. No se aplica a identificadores, códigos, DNI ni posibles categorías numéricas codificadas. Se pueden excluir manualmente columnas no reconocidas. El modo automático requiere al menos ocho valores finitos y tres valores distintos; constantes o muestras insuficientes se omiten.

Considera Z-score únicamente con n ≥ 30, |asimetría| ≤ 0,5, |curtosis excedente| ≤ 1, menos del 20% de repetición y extremo estandarizado ≤ 4. Es una heurística de normalidad aproximada, **no una prueba formal**. En otros casos prefiere IQR. Factores por defecto: IQR 1,5 y Z-score 3. Los métodos manuales de tratamiento permiten muestras desde tres observaciones y dos valores distintos para mantener el flujo V1; el diagnóstico usa el límite de ocho por defecto.

Calidad muestra método, justificación, límites, porcentaje y observaciones. Limpieza permite eliminar o limitar extremos según método elegido, siempre con vista previa y aprobación. Un atípico puede representar información valiosa; no se trata automáticamente ni penaliza el índice.

### Exportación y apariencia

**Exportación** conserva las descargas individuales V1 y agrega un libro con las tablas seleccionadas, historial y resumen de calidad opcionales. Los nombres de hojas se sanitizan a 31 caracteres y se desambiguarán si coinciden. Los datasets derivados también pueden descargarse individualmente.

El dashboard usa menú oscuro, tarjetas KPI, gráficos en dos columnas, componentes HTML/CSS y tablas con búsqueda, orden y paginación. Las tablas interactivas presentan hasta 2000 filas; cálculos y descargas usan todos los registros. Ambos temas afectan controles, tablas y Plotly sin cambiar datos. El tema se conserva en la sesión y en el parámetro `tema` de la URL; compartir la URL no comparte datasets. En móvil los gráficos pasan a una columna y las tarjetas a dos. Ver [validación y capturas](docs/VALIDATION.md).

El despliegue continúa usando `app.py`, Python 3.12 y `requirements.txt`; no necesita servicios de pago ni nuevas claves. `requirements-dev.txt` agrega únicamente Playwright para comprobaciones opcionales de navegador.
