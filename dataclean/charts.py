import plotly.express as px

KINDS = ['Barras', 'Columnas', 'Líneas', 'Histograma', 'Dispersión', 'Boxplot', 'Correlación', 'Circular', 'Temporal']


def make_chart(df, kind, x=None, y=None, aggregation='Sin agregar', dark=False):
    data = df.copy()
    if kind in ('Barras', 'Columnas', 'Líneas', 'Circular', 'Temporal') and aggregation != 'Sin agregar':
        if aggregation == 'Conteo': data = data.groupby(x, dropna=False).size().reset_index(name='Registros'); y = 'Registros'
        else:
            if y is None: raise ValueError('Seleccioná una columna numérica.')
            data = data.groupby(x, dropna=False)[y].agg({'Suma':'sum', 'Media':'mean', 'Mediana':'median'}[aggregation]).reset_index()
    if kind == 'Correlación':
        nums = data.select_dtypes(include='number')
        if len(nums.columns)<2: raise ValueError('La correlación requiere dos columnas numéricas.')
        fig = px.imshow(nums.corr(), text_auto='.2f', color_continuous_scale='RdBu', zmin=-1, zmax=1)
    elif kind == 'Histograma': fig = px.histogram(data, x=x)
    elif kind == 'Dispersión': fig = px.scatter(data, x=x, y=y)
    elif kind == 'Boxplot': fig = px.box(data, x=x, y=y)
    elif kind == 'Barras': fig = px.bar(data, x=y, y=x, orientation='h')
    elif kind == 'Columnas': fig = px.bar(data, x=x, y=y)
    elif kind == 'Circular':
        if data[x].nunique()>8: raise ValueError('Para más de ocho categorías usá barras.')
        if y is None or (data[y].dropna()<0).any(): raise ValueError('El circular requiere valores no negativos.')
        fig = px.pie(data, names=x, values=y)
    else: fig = px.line(data.sort_values(x), x=x, y=y, markers=True)
    fig.update_layout(template='plotly_dark' if dark else 'plotly_white', colorway=['#2563EB','#14B8A6','#16A34A','#EF4444'], margin=dict(l=20,r=20,t=40,b=20))
    return fig


def recommend_chart(df, x, y):
    import pandas as pd
    if pd.api.types.is_datetime64_any_dtype(df[x]): return 'Temporal: permite comparar evolución y variaciones por período.'
    if y and pd.api.types.is_numeric_dtype(df[x]) and pd.api.types.is_numeric_dtype(df[y]): return 'Dispersión: permite explorar asociaciones, segmentos y extremos; no prueba causalidad.'
    if pd.api.types.is_numeric_dtype(df[x]): return 'Histograma: permite reconocer dispersión, asimetría y valores extremos.'
    return 'Barras con agregación: permiten comparar categorías y su concentración para priorizar revisiones.'
