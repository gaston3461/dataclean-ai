import pandas as pd
from pandas.api.types import is_numeric_dtype, is_datetime64_any_dtype


def missing(df):
    return df.isna() | df.map(lambda x: isinstance(x, str) and not x.strip())


def semantic(s):
    name = str(s.name).lower()
    if is_datetime64_any_dtype(s): return 'Temporal'
    if name == 'id' or name.endswith('_id') or 'código' in name or 'codigo' in name: return 'Identificador'
    if any(x in name for x in ('fecha', 'date')): return 'Posible fecha'
    if any(x in name for x in ('ciudad', 'país', 'pais', 'provincia', 'latitud', 'longitud')): return 'Geográfica'
    if is_numeric_dtype(s):
        if any(x in name for x in ('precio', 'importe', 'venta', 'monto', 'factura')): return 'Importe monetario'
        if any(x in name for x in ('porcentaje', 'tasa', 'pct')): return 'Porcentaje'
        if any(x in name for x in ('cantidad', 'stock', 'unidades')): return 'Cantidad'
        return 'Numérica'
    return 'Categórica'


def profile(df):
    mask = missing(df)
    rows = []
    for col in df:
        s = df[col]
        rows.append({'Columna': col, 'Tipo Pandas': str(s.dtype), 'Tipo semántico': semantic(s),
                     'No nulos': int((~mask[col]).sum()), 'Faltantes': int(mask[col].sum()),
                     'Faltantes %': round(mask[col].mean()*100, 2), 'Únicos': s.nunique(),
                     'Ejemplos': ', '.join(map(str, s.dropna().unique()[:3])),
                     'Más frecuentes': str(s.value_counts().head(3).to_dict())})
    return pd.DataFrame(rows)


def metrics(df):
    return {'Filas': len(df), 'Columnas': len(df.columns), 'Celdas': df.size,
            'Memoria (MB)': round(df.memory_usage(deep=True).sum()/1024**2, 3),
            'Numéricas': len(df.select_dtypes(include='number').columns),
            'Categóricas': len(df.select_dtypes(include=['object', 'string', 'category']).columns),
            'Fechas': len(df.select_dtypes(include='datetime').columns),
            'Faltantes': int(missing(df).sum().sum()), 'Duplicados': int(df.duplicated().sum())}


def statistics(df):
    result = df.describe(include='all').astype(str).T
    result['suma (solo numéricas)'] = pd.Series({c: str(df[c].sum()) for c in df.select_dtypes(include='number')})
    return result


def date_profile(df):
    rows = []
    for c in df:
        if semantic(df[c]) in ('Temporal', 'Posible fecha'):
            parsed = pd.to_datetime(df[c], errors='coerce', dayfirst=True, format='mixed')
            rows.append({'Columna': c, 'Mínima': str(parsed.min()), 'Máxima': str(parsed.max()),
                         'Válidas': int(parsed.notna().sum()),
                         'Inválidas no vacías': int((parsed.isna() & ~missing(df)[c]).sum())})
    return pd.DataFrame(rows)
