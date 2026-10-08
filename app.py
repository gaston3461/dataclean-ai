from pathlib import Path
import json
import streamlit as st
import pandas as pd
import plotly.express as px
from dataclean.loading import load, sheets, detect_csv, MAX_BYTES
from dataclean.profiling import profile, metrics, statistics, date_profile, missing
from dataclean.quality import assess
from dataclean.cleaning import History, OPERATIONS, transform, affected
from dataclean.normalization import recommend
from dataclean.insights import insights
from dataclean.charts import KINDS, make_chart, recommend_chart
from dataclean.exporting import csv_bytes, excel_bytes, report_html

st.session_state.setdefault('approve_change', False)
st.set_page_config(page_title='DataClean AI — by Sánchez Gastón', page_icon='📊', layout='wide')
PAGES = ['Inicio e importación', 'Resumen del dataset', 'Calidad de datos', 'Limpieza y normalización',
         'Análisis e insights', 'Visualizaciones', 'Comparación', 'Exportación', 'Acerca de']
st.sidebar.title('📊 DataClean AI')
st.sidebar.caption('by Sánchez Gastón')
page = st.sidebar.radio('Navegación', PAGES)
theme = st.sidebar.selectbox('Tema', ['Claro', 'Oscuro'], key='theme')
dark = theme == 'Oscuro'
bg, fg, panel = ('#0F172A','#F8FAFC','#1E293B') if dark else ('#F8FAFC','#0F172A','#FFFFFF')
st.markdown(f'''<style>
.stApp {{background:{bg};color:{fg};}}
[data-testid="stSidebar"], [data-testid="stHeader"] {{background:{panel};color:{fg};}}
[data-testid="stMetric"] {{background:{panel};padding:16px;border-radius:12px;border-left:4px solid #14B8A6;}}
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"], [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{color:{fg};}}
.stButton button, .stDownloadButton button {{border-radius:8px;}}
</style>''', unsafe_allow_html=True)
st.title(page)
st.caption('Análisis estadístico y reglas inteligentes · Sin APIs ni servicios de pago')


def table(df):
    # Texto uniforme evita errores Arrow en tablas con estadísticas de tipos mixtos.
    st.dataframe(df, width='stretch', hide_index=True)


def kpis(df):
    vals = metrics(df)
    vals['Archivo (KB)'] = round(st.session_state.get('file_size',0)/1024, 1)
    items = list(vals.items())
    for i in range(0,len(items),4):
        for col, (label,value) in zip(st.columns(4),items[i:i+4]): col.metric(label,value)


def show_plot(fig):
    fig.update_layout(template='plotly_dark' if dark else 'plotly_white')
    st.plotly_chart(fig, width='stretch')


def set_data(df, name, size):
    st.session_state.history = History(df)
    st.session_state.file_name = name
    st.session_state.file_size = size
    st.session_state.pop('preview', None)


if page == PAGES[0]:
    st.write('Cargá un archivo Excel o CSV para explorar su calidad, revisar cambios y descargar resultados. Los datos permanecen en memoria durante esta sesión.')
    st.info('Límite: 20 MB y dos millones de celdas. No cargues información sensible en un despliegue público.')
    uploaded = st.file_uploader('Archivo CSV, XLSX o XLS', type=['csv','xlsx','xls'])
    if st.button('Usar dataset ficticio de ejemplo'):
        raw = (Path(__file__).parent/'data/ventas_ejemplo.csv').read_bytes()
        set_data(load(raw,'ventas_ejemplo.csv'), 'ventas_ejemplo.csv', len(raw))
        st.success('Ejemplo cargado.')
    if uploaded:
        raw = uploaded.getvalue()
        st.write(f'Archivo: {uploaded.name} · {len(raw)/1024:,.1f} KB')
        try:
            sheet, encoding, sep = 0, None, None
            if uploaded.name.lower().endswith('.csv'):
                enc, delimiter = detect_csv(raw)
                st.caption(f'Detección: {enc}; separador {repr(delimiter)}')
                encoding = st.selectbox('Codificación', list(dict.fromkeys([enc,'utf-8-sig','utf-8','cp1252','latin1'])))
                labels = {'Coma':',', 'Punto y coma':';', 'Tabulación':'\t', 'Barra vertical':'|'}
                selected = st.selectbox('Separador', list(labels), index=list(labels.values()).index(delimiter))
                sep = labels[selected]
            else: sheet = st.selectbox('Hoja Excel', sheets(raw,uploaded.name))
            a,b = st.columns(2)
            decimal = a.selectbox('Separador decimal', ['.', ','])
            thousands_label = b.selectbox('Separador de miles', ['Ninguno', '.', ','])
            st.caption('Las fechas se convierten explícitamente en Limpieza, con vista previa; así se evita perder fechas inválidas al importar.')
            if st.button('Importar archivo', type='primary'):
                with st.spinner('Leyendo archivo…'):
                    df = load(raw, uploaded.name, sheet=sheet, encoding=encoding, sep=sep,
                              decimal=decimal, thousands=None if thousands_label=='Ninguno' else thousands_label)
                    set_data(df,uploaded.name,len(raw))
                st.success('Importación completada.')
        except Exception as exc: st.error(str(exc))
    if 'history' in st.session_state:
        df = st.session_state.history.current
        st.subheader('Vista previa')
        rows = st.selectbox('Registros visibles',[10,25,50,100])
        table(df.head(rows)); kpis(df)
elif page == PAGES[8]:
    st.header('DataClean AI')
    st.write('by Sánchez Gastón')
    st.write('Proyecto de Ciencias de Datos e Inteligencia Artificial · Versión 1.0')
    st.write('Aplicación gratuita de análisis estadístico. No utiliza modelos remotos ni envía los datasets a APIs.')
    st.info('El índice de calidad y las recomendaciones son orientativos. Verificá las reglas de negocio antes de modificar datos.')
    st.write('Los archivos se procesan en memoria; no se almacenan en disco. La sesión conserva copias e historial hasta que se cierre o reinicie. La preferencia de tema se recuerda en la sesión.')
elif 'history' not in st.session_state:
    st.info('Primero cargá un archivo o el ejemplo desde Inicio e importación.')
else:
    history = st.session_state.history
    df = history.current
    st.caption(f'Dataset: {st.session_state.file_name} · {len(df):,} filas')
    if not len(df.columns) or not len(df):
        st.warning('El resultado está vacío. Podés deshacer o restablecer en Limpieza; exportar y comparar siguen disponibles.')
    if page == PAGES[1]:
        kpis(df)
        if len(df.columns):
            p = profile(df)
            query = st.text_input('Buscar columna')
            types = st.multiselect('Filtrar tipo semántico',p['Tipo semántico'].unique())
            p = p[p.Columna.astype(str).str.contains(query,case=False,regex=False)]
            if types: p = p[p['Tipo semántico'].isin(types)]
            table(p)
            st.subheader('Estadísticas descriptivas (todas las columnas)')
            table(statistics(df).reset_index(names='Columna'))
            if not date_profile(df).empty: st.subheader('Fechas'); table(date_profile(df))
            st.caption('Los identificadores numéricos se incluyen en la suma, pero esa suma generalmente no tiene significado de negocio.')
    elif page == PAGES[2]:
        keys = st.multiselect('Columnas clave para posibles duplicados',list(df.columns))
        method = st.selectbox('Método de atípicos',['IQR','Z-score'])
        ranges = {}
        nums = list(df.select_dtypes(include='number').columns)
        with st.expander('Rango válido definido por el usuario'):
            rc = st.selectbox('Columna numérica', ['Ninguna']+nums)
            if rc != 'Ninguna':
                low = st.number_input('Mínimo permitido',value=0.0)
                high = st.number_input('Máximo permitido',value=100.0)
                if low>high: st.error('El mínimo debe ser menor al máximo.')
                else: ranges[rc]=(low,high)
        result = assess(df,keys,ranges,method)
        st.metric('Índice orientativo de calidad',f'{result["score"]}/100')
        st.progress(result['score']/100)
        st.caption('50% completitud + 30% unicidad + 20% consistencia. Completitud: proporción de celdas no vacías. Unicidad: 1 − filas duplicadas/filas. Consistencia: 1 − celdas con espacios, variantes de categorías, fechas inválidas o fuera del rango definido/celdas. Cada celda se cuenta una vez. Atípicos y sospechas de tipo no penalizan. No es una certificación.')
        table(pd.DataFrame([result['components']]))
        table(result['issues'])
        if len(df.columns):
            show_plot(px.bar(x=list(df.columns),y=missing(df).sum(),labels={'x':'Columna','y':'Faltantes'},title='Valores faltantes'))
            types = df.dtypes.astype(str).value_counts()
            show_plot(px.bar(x=types.index,y=types.values,labels={'x':'Tipo','y':'Columnas'},title='Tipos de datos'))
        if not result['issues'].empty:
            grouped = result['issues'].groupby('Problema')['Registros'].sum().reset_index()
            show_plot(px.bar(grouped,x='Problema',y='Registros',title='Problemas detectados (pueden superponerse)'))
    elif page == PAGES[3]:
        tab1, tab2 = st.tabs(['Limpieza con aprobación','Normalización relacional'])
        with tab1:
            a,b = st.columns(2)
            if a.button('Deshacer',disabled=not history.records): history.undo(); st.session_state.pop('preview',None); st.rerun()
            reset = b.checkbox('Confirmar restablecimiento del original')
            if b.button('Restablecer',disabled=not reset): history.reset(); st.session_state.pop('preview',None); st.rerun()
            with st.form('transform'):
                operation = st.selectbox('Operación',OPERATIONS)
                cols = st.multiselect('Columnas afectadas (vacío = todas para duplicados)',list(df.columns))
                old = st.text_input('Valor a reemplazar (coincidencia exacta)')
                value = st.text_input('Nuevo valor / imputación personalizada')
                dayfirst = st.checkbox('Fechas con día antes del mes',value=True)
                method = st.selectbox('Detección para eliminar atípicos',['IQR','Z-score'])
                preview = st.form_submit_button('Preparar vista previa')
            if preview:
                try:
                    candidate = transform(df,operation,cols,value,old,dayfirst,method)
                    st.session_state.approve_change = False
                    st.session_state.preview = {'df':candidate,'operation':operation,'cols':cols}
                except Exception as exc: st.error(f'No se pudo preparar la operación: {exc}')
            pending = st.session_state.get('preview')
            if pending:
                candidate = pending['df']
                st.subheader(pending['operation'])
                st.write('Columnas: '+(', '.join(pending['cols']) or 'Todas'))
                st.write(f'Registros afectados: {affected(df,candidate)} · Filas: {len(df)} → {len(candidate)} · Columnas: {len(df.columns)} → {len(candidate.columns)}')
                st.warning('Revisá los cambios. Eliminar registros puede sesgar el análisis; imputar o reemplazar altera el significado. Las conversiones inválidas pasan a nulos. El original se conserva y podés deshacer.')
                a,b = st.columns(2)
                a.write('Antes'); a.dataframe(df.head(25),width='stretch')
                b.write('Después'); b.dataframe(candidate.head(25),width='stretch')
                approved = st.checkbox('Revisé la vista previa y apruebo esta transformación', key='approve_change')
                a,b = st.columns(2)
                if a.button('Aplicar',type='primary',disabled=not approved):
                    history.apply(candidate,pending['operation'],pending['cols']); st.session_state.pop('preview'); st.rerun()
                if b.button('Cancelar'): st.session_state.pop('preview'); st.rerun()
            if history.records: table(pd.DataFrame(history.records).astype(str))
        with tab2:
            keys = st.multiselect('Claves de negocio',list(df.columns),key='business_keys')
            st.caption('Indicá una dependencia de negocio para evaluar una propuesta: cada valor del determinante debería corresponder a un solo valor del dependiente.')
            determinant = st.selectbox('Determinante',['Sin indicar']+list(df.columns))
            dependent = st.selectbox('Atributo dependiente',['Sin indicar']+list(df.columns))
            deps = [(determinant,dependent)] if 'Sin indicar' not in (determinant,dependent) else []
            notes, proposals = recommend(df,keys,deps)
            for note in notes: st.info(note)
            for proposal in proposals:
                st.subheader(proposal['nombre']); st.write(proposal['relación']); table(proposal['tabla'])
            st.caption('Son propuestas explicativas: no modifican ni dividen automáticamente el dataset.')
    elif page == PAGES[4]:
        findings,recs,hypotheses = insights(df)
        for title,items in [('Hallazgos calculados',findings),('Recomendaciones de análisis',recs),('Hipótesis para investigar',hypotheses)]:
            st.subheader(title)
            for item in items: st.write('• '+item)
            if not items: st.caption('Sin evidencia suficiente en este dataset.')
    elif page == PAGES[5]:
        if len(df.columns):
            kind = st.selectbox('Gráfico',KINDS)
            x = st.selectbox('Eje X / categorías',list(df.columns))
            nums = list(df.select_dtypes(include='number').columns)
            ylabel = st.selectbox('Eje Y / medida',['Sin medida']+nums)
            y = None if ylabel=='Sin medida' else ylabel
            aggregation = st.selectbox('Agregación',['Sin agregar','Conteo','Suma','Media','Mediana'])
            filter_col = st.selectbox('Filtrar por columna',['Sin filtro']+list(df.columns))
            filtered = df
            if filter_col != 'Sin filtro':
                options = df[filter_col].dropna().astype(str).unique()[:1000]
                selected = st.multiselect('Valores incluidos (vacío = todos)',options)
                if selected: filtered = df[df[filter_col].astype(str).isin(selected)]
                st.caption('El selector muestra hasta 1000 valores únicos.')
            st.info(recommend_chart(df,x,y))
            if kind in ('Líneas','Temporal'): st.caption('Usá agregación para evitar múltiples puntos del mismo período. Temporal requiere convertir primero la columna de fechas.')
            try:
                if filtered.empty: raise ValueError('El filtro no contiene registros.')
                if kind=='Temporal' and not pd.api.types.is_datetime64_any_dtype(filtered[x]): raise ValueError('Convertí el eje X a fecha desde Limpieza.')
                if kind in ('Dispersión','Boxplot','Líneas','Temporal','Barras','Columnas') and y is None and aggregation!='Conteo': raise ValueError('Elegí una medida o agregación Conteo.')
                fig = make_chart(filtered,kind,x,y,aggregation,dark)
                show_plot(fig)
                st.download_button('Descargar gráfico HTML interactivo',fig.to_html(include_plotlyjs=True).encode(),'grafico.html','text/html')
            except Exception as exc: st.warning(f'No se puede generar este gráfico: {exc}')
    elif page == PAGES[6]:
        original = history.original
        before, after = metrics(original),metrics(df)
        comparison = pd.DataFrame({'Métrica':list(before),'Original':list(before.values()),'Actual':list(after.values())})
        table(comparison)
        st.write(f'Calidad: {assess(original)["score"]} → {assess(df)["score"]}')
        table(pd.DataFrame({'Original':original.dtypes.astype(str),'Actual':df.dtypes.astype(str)}).fillna('Columna eliminada/nueva').reset_index(names='Columna'))
        st.subheader('Historial de transformaciones activas')
        table(pd.DataFrame(history.records).astype(str))
    elif page == PAGES[7]:
        st.caption('Los textos que comienzan con =, +, − o @ se neutralizan para prevenir fórmulas de hojas de cálculo. El dataset en memoria no cambia.')
        sep_label = st.selectbox('Separador CSV',['Punto y coma','Coma','Tabulación'])
        sep = {'Punto y coma':';','Coma':',','Tabulación':'\t'}[sep_label]
        encoding = st.selectbox('Codificación de exportación',['utf-8-sig','utf-8','cp1252'])
        decimal = st.selectbox('Decimal CSV',[',','.'])
        try: st.download_button('Dataset limpio CSV',csv_bytes(df,sep,encoding,decimal),'dataclean.csv','text/csv')
        except Exception as exc: st.error(f'No se puede exportar con esa codificación: {exc}. Probá UTF-8.')
        try: st.download_button('Dataset limpio Excel',excel_bytes(df),'dataclean.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        except Exception as exc: st.error(f'No se pudo exportar Excel: {exc}')
        st.download_button('Historial JSON',json.dumps(history.records,ensure_ascii=False,indent=2),'historial.json','application/json')
        if len(df.columns):
            st.download_button('Informe de calidad HTML',report_html(df,history.records),'informe_calidad.html','text/html')
            st.download_button('Resumen estadístico CSV',csv_bytes(statistics(df).reset_index(names='Columna')),'resumen.csv','text/csv')
st.divider()
st.caption('DataClean AI · by Sánchez Gastón · Versión 1.0')
