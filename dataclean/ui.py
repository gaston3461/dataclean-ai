"""Componentes visuales con estilos por sesión; ningún tema global mutable."""
import html
import json
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from .profiling import metrics
from .quality import assess
from .automatic import select_visualizations, render_visualization, analysis_frame
from .insights import insights


def apply_theme(dark):
    bg,fg,panel,muted,border=('#09111F','#E6EDF8','#111C30','#95A4BC','#24324A') if dark else ('#F3F6FB','#14243B','#FFFFFF','#63758D','#DFE7F1')
    st.markdown(f'''<style>
    :root {{ --dc-bg:{bg}; --dc-fg:{fg}; --dc-panel:{panel}; --dc-muted:{muted}; --dc-border:{border}; }}
    .stApp, [data-testid="stAppViewContainer"] {{background:var(--dc-bg);color:var(--dc-fg);}}
    [data-testid="stHeader"] {{background:var(--dc-bg);color:var(--dc-fg);}}
    [data-testid="stHeader"] svg, [data-testid="stSidebarCollapsedControl"] svg {{color:var(--dc-fg)!important;fill:var(--dc-fg)!important;}}
    [data-testid="stMainBlockContainer"] {{padding-top:3.4rem;padding-bottom:2rem;max-width:1540px;}}
    [data-testid="stSidebar"] {{background:#101B2F;border-right:1px solid #22334B;}}
    [data-testid="stSidebar"] * {{color:#E6EDF8;}}
    [data-testid="stSidebar"] [data-baseweb="select"] > div {{background:#1B2B43!important;border-color:#32445F!important;}}
    [data-testid="stSidebar"] [role="radiogroup"] label {{padding:8px 10px;border-radius:8px;margin:2px 0;}}
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {{background:#203250;}}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{background:#203250;}}
    [data-testid="stMain"] [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"],
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"], [data-testid="stCaptionContainer"] {{color:var(--dc-fg);}}
    [data-testid="stMain"] [data-baseweb="select"] > div, [data-testid="stMain"] [data-baseweb="input"],
    [data-testid="stMain"] [data-baseweb="textarea"], [data-testid="stMain"] input,
    [data-testid="stMain"] textarea {{background:var(--dc-panel)!important;color:var(--dc-fg)!important;border-color:var(--dc-border)!important;}}
    [data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"], [role="option"] {{background:var(--dc-panel)!important;color:var(--dc-fg)!important;}}
    [data-testid="stMain"] [data-baseweb="select"] svg {{fill:var(--dc-fg)!important;}}
    [data-baseweb="tag"] {{background:#233E70!important;color:#EFF6FF!important;}}
    [data-testid="stFileUploaderDropzone"], [data-testid="stForm"], [data-testid="stExpander"] {{background:var(--dc-panel);color:var(--dc-fg);border-color:var(--dc-border);border-radius:12px;}}
    [data-testid="stAlert"] {{background:var(--dc-panel);border:1px solid var(--dc-border);border-radius:10px;}}
    [data-testid="stAlert"] p {{color:var(--dc-fg);}}
    [data-testid="stMetric"] {{background:var(--dc-panel);padding:18px;border:1px solid var(--dc-border);border-radius:14px;}}
    .stButton button, .stDownloadButton button, [data-testid="stFormSubmitButton"] button {{border-radius:9px;min-height:42px;}}
    button[kind="secondary"], [data-testid="stDownloadButton"] button {{background:var(--dc-panel);color:var(--dc-fg);border-color:var(--dc-border);}}
    button[kind="primary"] {{background:#2563EB;color:white;border:none;}}
    [data-testid="stTabs"] button {{color:var(--dc-muted);}}
    [data-testid="stTabs"] button[aria-selected="true"] {{color:#3B82F6;}}
    .dc-brand {{display:flex;gap:12px;align-items:center;margin:10px 0 26px;}}
    .dc-logo {{width:44px;height:44px;border-radius:12px;background:linear-gradient(135deg,#2563EB,#14B8A6);display:grid;place-items:center;font-size:25px;color:white;}}
    .dc-brand strong {{font-size:21px;letter-spacing:-.5px;}} .dc-brand small {{display:block;color:#95A4BC!important;font-size:11px;margin-top:3px;}}
    .dc-hero {{display:flex;justify-content:space-between;gap:20px;align-items:center;margin-bottom:22px;}}
    .dc-eyebrow {{font-size:11px;font-weight:700;letter-spacing:1.6px;color:#3B82F6;text-transform:uppercase;margin-bottom:7px;}}
    .dc-hero h1 {{font-size:clamp(25px,3vw,34px);letter-spacing:-1px;color:var(--dc-fg);padding:0;margin:0 0 8px;}}
    .dc-hero p {{color:var(--dc-muted);font-size:14px;margin:0;}}
    .dc-badge {{border:1px solid var(--dc-border);border-radius:24px;padding:8px 14px;background:var(--dc-panel);font-size:12px;white-space:nowrap;color:var(--dc-fg);}}
    .dc-kpis {{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin:8px 0 24px;}}
    .dc-kpi {{background:var(--dc-panel);border:1px solid var(--dc-border);border-radius:14px;padding:19px 20px;box-shadow:0 4px 18px #00000004;}}
    .dc-kpi-top {{display:flex;justify-content:space-between;align-items:center;color:var(--dc-muted);font-size:12px;font-weight:600;}}
    .dc-kpi-icon {{background:#2563EB15;color:#3B82F6;border-radius:9px;padding:6px 9px;font-size:16px;}}
    .dc-kpi-value {{font-size:29px;line-height:1.3;color:var(--dc-fg);font-weight:700;margin-top:10px;letter-spacing:-.7px;}}
    .dc-kpi-hint {{font-size:11px;color:var(--dc-muted);margin-top:5px;}}
    .dc-section {{display:flex;align-items:center;gap:10px;margin:12px 0 4px;}}
    .dc-section .dc-section-title {{font-size:19px;font-weight:700;color:var(--dc-fg);padding:0;}}
    .dc-section > span {{font-size:10px;padding:4px 8px;border-radius:5px;color:#3B82F6;background:#2563EB15;}}
    [data-testid="stPlotlyChart"] {{border:1px solid var(--dc-border);border-radius:13px;overflow:hidden;background:var(--dc-panel);}}
    .dc-foot {{font-size:11px;color:var(--dc-muted);display:flex;justify-content:space-between;padding-top:16px;border-top:1px solid var(--dc-border);margin-top:30px;}}
    @media(max-width:1000px) {{.dc-kpis {{grid-template-columns:repeat(2,minmax(0,1fr));}}}}
    @media(max-width:640px) {{.dc-kpis {{gap:10px;}}.dc-kpi {{padding:12px;}}.dc-kpi-value {{font-size:23px;}}.dc-hero {{align-items:flex-start;flex-direction:column;gap:10px;}}[data-testid="stHorizontalBlock"] {{flex-wrap:wrap;}}[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{min-width:100%!important;}}[data-testid="stMainBlockContainer"] {{padding:3.4rem 1rem 1.2rem;}}}}
    </style>''',unsafe_allow_html=True)


def hero(title,subtitle):
    st.markdown(f'<div class="dc-hero"><div><div class="dc-eyebrow">ESPACIO DE ANÁLISIS DE DATOS</div><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div><span class="dc-badge">● &nbsp;Análisis local · V2.0</span></div>',unsafe_allow_html=True)


def kpi_cards(df,size=0,full=False):
    m=metrics(df); quality=assess(df)['score']
    values=[('Filas',f'{len(df):,}','▤','Registros del dataset activo'),('Columnas',str(len(df.columns)),'▥','Variables disponibles'),
            ('Calidad orientativa',f'{quality:.1f}/100','◈','No es una certificación'),('Valores faltantes',f'{m["Faltantes"]:,}','◌','Incluye textos vacíos')]
    if full:
        values += [('Duplicados',str(m['Duplicados']),'⧉','Filas completas repetidas'),('Memoria',f'{m["Memoria (MB)"]:.3f} MB','▣','Memoria del DataFrame'),
                   ('Celdas',f'{df.size:,}','▦',f'{m["Numéricas"]} numéricas · {m["Fechas"]} fechas'),('Archivo',f'{size/1024:.1f} KB','↥','Tamaño de origen; un libro comparte tamaño')]
    cards=''.join(f'<div class="dc-kpi"><div class="dc-kpi-top">{label}<span class="dc-kpi-icon">{icon}</span></div><div class="dc-kpi-value">{value}</div><div class="dc-kpi-hint">{hint}</div></div>' for label,value,icon,hint in values)
    st.markdown('<div class="dc-kpis">'+cards+'</div>',unsafe_allow_html=True)


def professional_table(df,dark=False):
    """Tabla aislada con búsqueda, orden y paginación; colores controlados por sesión."""
    limited=df.head(2000).copy()
    rows=limited.astype('string').fillna('—').values.tolist()
    cols=list(map(str,limited.columns))
    payload=json.dumps({'cols':cols,'rows':rows},ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    bg,fg,muted,border,head=('#111C30','#E6EDF8','#95A4BC','#24324A','#17263E') if dark else ('#FFFFFF','#14243B','#63758D','#DFE7F1','#F6F8FC')
    source='''<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
    *{box-sizing:border-box}body{margin:0;font:12px Arial,sans-serif;background:BG;color:FG}
    .shell{border:1px solid BORDER;border-radius:12px;overflow:hidden}.toolbar{display:flex;justify-content:space-between;gap:10px;padding:12px;background:BG;align-items:center}
    input{background:HEAD;color:FG;border:1px solid BORDER;border-radius:7px;padding:9px;width:min(240px,70%)}
    .scroll{overflow:auto;max-height:300px}table{border-collapse:collapse;width:100%;white-space:nowrap}th{position:sticky;top:0;background:HEAD;text-align:left;padding:12px;cursor:pointer;color:MUTED;font-size:11px}td{padding:11px 12px;border-top:1px solid BORDER;max-width:480px;overflow:hidden;text-overflow:ellipsis}tr:hover{background:HEAD}
    footer{padding:10px 12px;display:flex;justify-content:space-between;align-items:center;color:MUTED;border-top:1px solid BORDER}button{background:HEAD;color:FG;border:1px solid BORDER;border-radius:5px;padding:5px 9px;cursor:pointer}button:disabled{opacity:.4}
    </style></head><body><div class="shell"><div class="toolbar"><input id="q" placeholder="Buscar en tabla…" aria-label="Buscar en tabla"><span id="n"></span></div><div class="scroll"><table><thead><tr id="head"></tr></thead><tbody id="body"></tbody></table></div><footer><span id="page"></span><div><button id="prev">←</button> <button id="next">→</button></div></footer></div><script>
    const data=PAYLOAD;let filtered=data.rows.slice(),page=0,sortCol=-1,asc=true;const $=id=>document.getElementById(id);
    const cell=(tag,text)=>{const el=document.createElement(tag);el.textContent=text;el.title=text;return el;};
    data.cols.forEach((col,i)=>{const th=cell('th',col+' ↕');th.onclick=()=>{asc=sortCol===i?!asc:true;sortCol=i;filtered.sort((a,b)=>String(a[i]).localeCompare(String(b[i]),'es',{numeric:true})*(asc?1:-1));page=0;render();};$('head').append(th);});
    function render(){$('body').replaceChildren();filtered.slice(page*25,(page+1)*25).forEach(row=>{const tr=document.createElement('tr');row.forEach(value=>tr.append(cell('td',value)));$('body').append(tr);});$('n').textContent=filtered.length+' registros';$('page').textContent='Página '+(page+1)+' de '+Math.max(1,Math.ceil(filtered.length/25));$('prev').disabled=page===0;$('next').disabled=(page+1)*25>=filtered.length;}
    $('q').oninput=()=>{const q=$('q').value.toLocaleLowerCase('es');filtered=data.rows.filter(row=>row.some(v=>String(v).toLocaleLowerCase('es').includes(q)));page=0;render();};$('prev').onclick=()=>{page--;render();};$('next').onclick=()=>{page++;render();};render();
    </script></body></html>'''
    for marker,value in [('BORDER',border),('MUTED',muted),('HEAD',head),('BG',bg),('FG',fg),('PAYLOAD',payload)]: source=source.replace(marker,value)
    components.html(source,height=min(410,130+min(len(limited),10)*34),scrolling=False)
    if len(df)>2000: st.caption('Tabla interactiva limitada a 2000 filas. El análisis y las descargas usan el dataset completo.')


def automatic_dashboard(df,dark=False,prefix='dashboard',with_insights=True):
    kpi_cards(df)
    frame,inferred=analysis_frame(df)
    a,b=st.columns([3,1])
    a.markdown('<div class="dc-section"><div class="dc-section-title">Visualizaciones recomendadas</div><span>AUTOMÁTICAS</span></div>',unsafe_allow_html=True)
    limit=b.selectbox('Cantidad de gráficos',[6,4,8],key=f'{prefix}_limit')
    filtered=df
    with st.expander('Filtros y variables detectadas',expanded=False):
        categories=[c for c,r in inferred.items() if r in ('Categórica','Geográfica','Categoría codificada') and 1<df[c].nunique()<=1000]
        col=st.selectbox('Filtrar categoría',['Sin filtro']+categories,key=f'{prefix}_filter')
        if col!='Sin filtro':
            options=st.multiselect('Valores incluidos',df[col].dropna().astype(str).unique(),key=f'{prefix}_values_{col}')
            if options: filtered=filtered[filtered[col].astype(str).isin(options)]
        datecols=[c for c,r in inferred.items() if r=='Temporal']
        datecol=st.selectbox('Filtrar período',['Sin filtro']+datecols,key=f'{prefix}_date')
        if datecol!='Sin filtro':
            dates=frame[datecol].dropna()
            if len(dates):
                period=st.date_input('Período incluido',value=(dates.min().date(),dates.max().date()),key=f'{prefix}_period_{datecol}')
                if len(period)==2:
                    mask=frame[datecol].dt.date.between(period[0],period[1]); filtered=filtered.loc[mask.fillna(False)]
        professional_table(pd.DataFrame({'Columna':list(inferred),'Rol inferido':list(inferred.values())}),dark)
    if len(filtered)!=len(df): st.caption(f'Filtro activo: {len(filtered):,} de {len(df):,} registros. KPIs superiores corresponden al dataset completo; gráficos y conclusiones al filtro.')
    specs=select_visualizations(filtered,limit)
    if not specs: st.info('No hay suficiente variabilidad o datos válidos para recomendar gráficos. Podés revisar tipos y usar el editor manual.')
    elif len(specs)<4: st.caption(f'Se generaron {len(specs)} gráficos con evidencia suficiente; no se agregan visualizaciones redundantes para completar una cantidad fija.')
    for i in range(0,len(specs),2):
        columns=st.columns(2)
        for column,spec in zip(columns,specs[i:i+2]):
            with column:
                try:
                    fig,conclusion=render_visualization(filtered,spec,dark)
                    st.plotly_chart(fig,width='stretch',theme=None,key=f'{prefix}_{i}_{spec["key"]}')
                    st.caption(f'Selección {spec["score"]}/100 · {spec["reason"]}')
                    st.write(f'**Pregunta:** {spec["question"]}')
                    st.write(f'**Dato calculado:** {conclusion}')
                    with st.expander('Exportar y ver configuración'):
                        st.write(f'Variables: {spec["x"] or "matriz"} · {spec["y"] or "frecuencia"}')
                        st.download_button('Descargar gráfico HTML',fig.to_html(include_plotlyjs=True).encode(),'grafico_auto.html','text/html',key=f'download_{prefix}_{spec["key"]}')
                except (ValueError,TypeError) as exc: st.info(f'Gráfico omitido por datos insuficientes: {exc}')
    if with_insights:
        findings,recs,hypotheses=insights(filtered)
        a,b=st.columns(2)
        with a:
            st.subheader('Hallazgos calculados')
            for item in findings[:5]: st.write('• '+item)
        with b:
            st.subheader('Preguntas para profundizar')
            for item in recs[:4]: st.write('• '+item)
            st.caption('Las asociaciones observadas no demuestran causalidad.')
