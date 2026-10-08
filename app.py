from pathlib import Path
import json
import streamlit as st
import pandas as pd
import plotly.express as px
from dataclean.loading import load, sheets, detect_csv, MAX_BYTES, load_workbook
from dataclean.profiling import profile, metrics, statistics, date_profile, missing
from dataclean.quality import assess
from dataclean.cleaning import History, OPERATIONS, transform, affected
from dataclean.normalization import recommend
from dataclean.insights import insights
from dataclean.charts import KINDS, make_chart, recommend_chart
from dataclean.exporting import csv_bytes, excel_bytes, report_html, workbook_bytes
from dataclean.workspace import Workspace
from dataclean.ui import apply_theme, hero, kpi_cards, professional_table, automatic_dashboard
from dataclean.consolidation_ui import consolidation_panel
from dataclean.outliers import outlier_table
from dataclean.roles import roles

st.session_state.setdefault('approve_change', False)
st.session_state.setdefault('approve_consolidation', False)
st.session_state.setdefault('confirm_join_risk', False)
st.session_state.setdefault('derived_name', 'Consolidado')
st.session_state.setdefault('theme', 'Oscuro' if st.query_params.get('tema') == 'oscuro' else 'Claro')
st.set_page_config(page_title='DataClean AI — by Sánchez Gastón', page_icon='📊', layout='wide')
PAGES = ['Inicio e importación', 'Resumen del dataset', 'Calidad de datos', 'Limpieza y normalización',
         'Análisis e insights', 'Visualizaciones', 'Comparación', 'Exportación', 'Acerca de', 'Dashboard automático', 'Relaciones y consolidación']
st.sidebar.markdown('<div class="dc-brand"><div class="dc-logo">▥</div><div><strong>DataClean AI</strong><small>by Sánchez Gastón</small></div></div>', unsafe_allow_html=True)
page = st.sidebar.radio('Navegación', [PAGES[0], PAGES[9], *PAGES[1:8], PAGES[10], PAGES[8]])
theme = st.sidebar.selectbox('Tema', ['Claro', 'Oscuro'], key='theme')
dark = theme == 'Oscuro'
st.query_params['tema'] = 'oscuro' if dark else 'claro'
apply_theme(dark)
if 'workspace' not in st.session_state:
    st.session_state.workspace = Workspace()
    if 'history' in st.session_state:
        key = st.session_state.workspace.add(st.session_state.history.current, st.session_state.get('file_name','Dataset'))
        st.session_state.workspace.datasets[key].history = st.session_state.history
workspace = st.session_state.workspace
if workspace.datasets:
    selected = st.sidebar.selectbox('Dataset activo', list(workspace.datasets),
        index=list(workspace.datasets).index(workspace.active),
        format_func=lambda k: f'{workspace.datasets[k].name} · {k}', key=f'dataset_selector_{workspace.active}')
    if selected != workspace.active:
        workspace.select(selected)
        st.session_state.pop('preview', None)
        st.session_state.approve_change = False
    active = workspace.datasets[workspace.active]
    st.session_state.history = active.history
    st.session_state.file_name = active.name
    st.session_state.file_size = active.size
hero(page, 'Explorá datos, detectá oportunidades y tomá decisiones con evidencia.')


def table(df):
    professional_table(df, dark)


def kpis(df):
    kpi_cards(df, st.session_state.get('file_size', 0), full=True)


def show_plot(fig):
    fig.update_layout(template='plotly_dark' if dark else 'plotly_white')
    st.plotly_chart(fig, width='stretch', theme=None)


def set_data(df, name, size, source='Archivo importado'):
    workspace.add(df, name, source, size)
    st.session_state.history = workspace.datasets[workspace.active].history
    st.session_state.file_name = name
    st.session_state.file_size = size
    st.session_state.pop('preview', None)


if page == PAGES[0]:
    st.write('Importá un libro completo o varios CSV. Cada tabla conserva sus propios cambios y su historial durante la sesión.')
    with st.expander('Importación de archivos', expanded=not bool(workspace.datasets)):
        st.caption('20 MB por archivo · dos millones de celdas por libro · hasta 40 datasets por sesión.')
        uploaded_files = st.file_uploader('Archivos CSV, XLSX o XLS', type=['csv','xlsx','xls'], accept_multiple_files=True)
        settings={}
        for index,uploaded in enumerate(uploaded_files):
            raw=uploaded.getvalue()
            st.write(f'**{uploaded.name}** · {len(raw)/1024:,.1f} KB')
            try:
                encoding,sep=None,None
                if uploaded.name.lower().endswith('.csv'):
                    enc,delimiter=detect_csv(raw)
                    a,b=st.columns(2)
                    encoding=a.selectbox('Codificación',list(dict.fromkeys([enc,'utf-8-sig','utf-8','cp1252','latin1'])),key=f'enc_{index}')
                    labels={'Coma':',','Punto y coma':';','Tabulación':'\t','Barra vertical':'|'}
                    selected=b.selectbox('Separador',list(labels),index=list(labels.values()).index(delimiter),key=f'sep_{index}')
                    sep=labels[selected]
                else:
                    names=sheets(raw,uploaded.name)
                    st.caption('Hojas detectadas: '+', '.join(names)+'. Se importarán todas, incluidas hojas vacías.')
                a,b=st.columns(2)
                decimal=a.selectbox('Separador decimal',['.',','],key=f'decimal_{index}')
                thousands=b.selectbox('Separador de miles',['Ninguno','.',','],key=f'thousands_{index}')
                settings[index]={'encoding':encoding,'sep':sep,'decimal':decimal,'thousands':None if thousands=='Ninguno' else thousands}
            except Exception as exc: st.error(str(exc))
        if uploaded_files and st.button('Importar archivos',type='primary'):
            try:
                staged=[]
                with st.spinner('Importando tablas y preparando su perfil…'):
                    for index,uploaded in enumerate(uploaded_files):
                        if index not in settings: raise ValueError('Hay archivos inválidos; corregilos antes de importar.')
                        raw=uploaded.getvalue(); opts=settings[index]
                        if uploaded.name.lower().endswith('.csv'):
                            staged.append((load(raw,uploaded.name,**opts),uploaded.name,len(raw),uploaded.name))
                        else:
                            frames=load_workbook(raw,uploaded.name,decimal=opts['decimal'],thousands=opts['thousands'])
                            staged.extend((df,name,len(raw),uploaded.name) for name,df in frames.items())
                    if len(workspace.datasets)+len(staged)>40: raise ValueError('La importación excede 40 datasets. No se importó ninguna tabla.')
                    if sum(df.size for df,*_ in staged)+sum(d.history.current.size for d in workspace.datasets.values())>4_000_000:
                        raise ValueError('La sesión supera cuatro millones de celdas. No se importó ninguna tabla.')
                    for df,name,size,source in staged: set_data(df,name,size,source)
                st.rerun()
            except Exception as exc: st.error(f'Importación no realizada: {exc}')
        if st.button('Usar dataset ficticio de ejemplo'):
            raw=(Path(__file__).parent/'data/ventas_ejemplo.csv').read_bytes()
            try:
                set_data(load(raw,'ventas_ejemplo.csv'),'ventas_ejemplo.csv',len(raw),'Ejemplo ficticio')
                st.rerun()
            except ValueError as exc: st.error(str(exc))
    if workspace.datasets:
        with st.expander('Tablas de la sesión y calidad por hoja'):
            table(pd.DataFrame(workspace.summary()))
        st.subheader(f'Dashboard · {workspace.datasets[workspace.active].name}')
        automatic_dashboard(st.session_state.history.current,dark,f'home_{workspace.active}')
        with st.expander('Vista previa de registros'):
            rows=st.selectbox('Registros visibles',[10,25,50,100])
            table(st.session_state.history.current.head(rows))
    else:
        st.markdown('<div class="dc-kpis"><div class="dc-kpi"><div class="dc-kpi-icon">↥</div><h3>1. Importá</h3><p>Excel y CSV, sin programar.</p></div><div class="dc-kpi"><div class="dc-kpi-icon">◈</div><h3>2. Explorá</h3><p>Perfil, calidad y gráficos automáticos.</p></div><div class="dc-kpi"><div class="dc-kpi-icon">⧉</div><h3>3. Consolidá</h3><p>Relacioná tablas con evidencia.</p></div><div class="dc-kpi"><div class="dc-kpi-icon">↓</div><h3>4. Exportá</h3><p>Resultados e informes listos para usar.</p></div></div>',unsafe_allow_html=True)

elif page == PAGES[8]:
    st.header('DataClean AI')
    st.write('by Sánchez Gastón')
    st.write('Proyecto de Ciencias de Datos e Inteligencia Artificial · Versión 2.0')
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
        method = st.selectbox('Método de atípicos',['Automático','IQR','Z-score'])
        iqr_factor = st.number_input('Factor IQR',min_value=0.1,max_value=10.0,value=1.5,step=0.1)
        z_threshold = st.number_input('Umbral Z-score',min_value=0.1,max_value=10.0,value=3.0,step=0.1)
        ranges = {}
        nums = list(df.select_dtypes(include='number').columns)
        with st.expander('Rango válido definido por el usuario'):
            rc = st.selectbox('Columna numérica', ['Ninguna']+nums)
            if rc != 'Ninguna':
                low = st.number_input('Mínimo permitido',value=0.0)
                high = st.number_input('Máximo permitido',value=100.0)
                if low>high: st.error('El mínimo debe ser menor al máximo.')
                else: ranges[rc]=(low,high)
        result = assess(df,keys,ranges,method,iqr_factor,z_threshold)
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
        st.subheader('Diagnóstico de valores atípicos')
        st.info('Un valor atípico no necesariamente es un error: puede contener información importante. No se modifica ningún valor desde este diagnóstico.')
        exclusions=st.multiselect('Excluir variables codificadas o identificadores no reconocidos',nums)
        summary,details=outlier_table(df,method=method,iqr_factor=iqr_factor,z_threshold=z_threshold)
        if exclusions:
            from dataclean.outliers import analyze_outliers
            for col in exclusions: details[col]=analyze_outliers(df[col],exclude=True)
            for col in exclusions:
                summary.loc[summary.Columna==col,['Método','Justificación','Atípicos','Registros %']]=['Omitido','Excluida por el usuario',0,0.0]
        table(summary)
        selected_outlier=st.selectbox('Revisar observaciones de una columna',['Ninguna']+nums)
        if selected_outlier!='Ninguna':
            detail=details[selected_outlier]
            st.write(detail['reason'])
            table(df.loc[detail['mask']].head(100))
            if detail['count']>100: st.caption('Se muestran las primeras 100 observaciones atípicas.')
            a,b=st.columns(2)
            with a: show_plot(px.histogram(df,x=selected_outlier,title='Distribución observada'))
            with b: show_plot(px.box(df,y=selected_outlier,title='Dispersión y valores extremos'))
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
                method = st.selectbox('Detección para eliminar o limitar atípicos',['Automático','IQR','Z-score'])
                iqr_factor = st.number_input('Factor IQR para tratamiento',min_value=0.1,max_value=10.0,value=1.5,step=0.1)
                z_threshold = st.number_input('Umbral Z-score para tratamiento',min_value=0.1,max_value=10.0,value=3.0,step=0.1)
                preview = st.form_submit_button('Preparar vista previa')
            if preview:
                try:
                    candidate = transform(df,operation,cols,value,old,dayfirst,method,iqr_factor,z_threshold)
                    st.session_state.approve_change = False
                    st.session_state.preview = {'df':candidate,'operation':operation,'cols':cols,'revision':history.revision,'dataset':workspace.active,'parameters':{'método':method,'factor_IQR':iqr_factor,'umbral_Z':z_threshold,'día_primero':dayfirst,'valor_anterior':old,'nuevo_valor':value}}
                except Exception as exc: st.error(f'No se pudo preparar la operación: {exc}')
            pending = st.session_state.get('preview')
            if pending and pending.get('revision')==history.revision and pending.get('dataset')==workspace.active:
                candidate = pending['df']
                st.subheader(pending['operation'])
                st.write('Columnas: '+(', '.join(pending['cols']) or 'Todas'))
                st.write(f'Registros afectados: {affected(df,candidate)} · Filas: {len(df)} → {len(candidate)} · Columnas: {len(df.columns)} → {len(candidate.columns)}')
                st.warning('Revisá los cambios. Eliminar registros puede sesgar el análisis; imputar o reemplazar altera el significado. Las conversiones inválidas pasan a nulos. El original se conserva y podés deshacer.')
                a,b = st.columns(2)
                with a: st.write('Antes'); table(df.head(25))
                with b: st.write('Después'); table(candidate.head(25))
                approved = st.checkbox('Revisé la vista previa y apruebo esta transformación', key='approve_change')
                a,b = st.columns(2)
                if a.button('Aplicar',type='primary',disabled=not approved):
                    history.apply(candidate,pending['operation'],pending['cols'],pending['parameters']); st.session_state.pop('preview'); st.rerun()
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
        auto,manual=st.tabs(['Visualizaciones automáticas','Editor manual'])
        with auto:
            automatic_dashboard(df,dark,f'visual_{workspace.active}',with_insights=False)
        with manual:
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
        st.subheader('Libro completo de la sesión')
        include_history=st.checkbox('Incluir hoja de historial',value=True)
        include_quality=st.checkbox('Incluir hoja de resumen de calidad',value=True)
        export_keys=st.multiselect('Tablas a exportar',list(workspace.datasets),default=list(workspace.datasets),format_func=lambda k:f'{workspace.datasets[k].name} · {k}')
        if export_keys:
            named={}; histories={}
            for key in export_keys:
                dataset=workspace.datasets[key]; label=dataset.name
                if label in named: label=f'{label}_{key}'
                named[label]=dataset.history.current; histories[label]=dataset.history.records
            try:
                st.download_button('Descargar libro multitabla',workbook_bytes(named,histories if include_history else None,include_quality),'dataclean_completo.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            except Exception as exc: st.error(f'No se pudo exportar el libro: {exc}')
    elif page == PAGES[9]:
        automatic_dashboard(df,dark,f'dashboard_{workspace.active}')
        if workspace.datasets[workspace.active].lineage:
            with st.expander('Origen del dataset derivado'):
                st.json(workspace.datasets[workspace.active].lineage)
    elif page == PAGES[10]:
        consolidation_panel(workspace,dark)
st.markdown('<div class="dc-foot"><span>DataClean AI · by Sánchez Gastón</span><span>Versión 2.0 · Sin servicios de pago</span></div>',unsafe_allow_html=True)
