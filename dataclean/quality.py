import numpy as np
import pandas as pd
from .profiling import missing, semantic


def outlier_mask(s, method='IQR'):
    if method == 'Z-score':
        std = s.std(ddof=0)
        return ((s-s.mean()).abs()/std > 3).fillna(False) if std and np.isfinite(std) else pd.Series(False, index=s.index)
    q1, q3 = s.quantile([.25, .75]); span = q3-q1
    return ((s < q1-1.5*span) | (s > q3+1.5*span)).fillna(False)


def assess(df, keys=(), ranges=None, method='Automático', iqr_factor=1.5, z_threshold=3.0):
    nulls = missing(df)
    if not df.size:
        return {'score':0.0,'components':{'Completitud':0.0,'Unicidad':0.0,'Consistencia':0.0},
                'issues':pd.DataFrame([{'Columna':'Todas','Problema':'Dataset sin celdas evaluables','Registros':len(df)}])}
    issues = []
    inconsistent = pd.DataFrame(False, index=df.index, columns=df.columns)
    def add(c, label, mask, consistency=False):
        n = int(mask.sum())
        if n:
            issues.append({'Columna': c, 'Problema': label, 'Registros': n})
            if consistency: inconsistent[c] |= mask
    for c in df:
        s = df[c]
        add(c, 'Valores faltantes', nulls[c])
        if nulls[c].mean() > .5: issues.append({'Columna': c, 'Problema': 'Más del 50% faltante', 'Registros': int(nulls[c].sum())})
        if s.nunique(dropna=True) <= 1: issues.append({'Columna': c, 'Problema': 'Columna constante', 'Registros': len(s)})
        if pd.api.types.is_numeric_dtype(s):
            from .outliers import analyze_outliers
            detail = analyze_outliers(s, method, iqr_factor, z_threshold)
            add(c, 'Atípicos ('+detail['method']+')', detail['mask'])
            if ranges and c in ranges:
                low, high = ranges[c]; add(c, 'Fuera de rango indicado', ((s<low)|(s>high)).fillna(False), True)
        else:
            text = s.map(lambda x: x if isinstance(x, str) else None)
            stripped = text.str.strip()
            add(c, 'Espacios innecesarios', (text.notna() & text.ne(stripped)), True)
            canonical = stripped.str.casefold()
            variants = pd.DataFrame({'raw': text, 'norm': canonical}).dropna().groupby('norm')['raw'].nunique()
            add(c, 'Variantes de categorías/mayúsculas', canonical.isin(variants[variants>1].index), True)
            if semantic(s) == 'Posible fecha':
                parsed = pd.to_datetime(s, errors='coerce', dayfirst=True, format='mixed')
                add(c, 'Fechas inválidas / tipo temporal pendiente', parsed.isna() & ~nulls[c], True)
            elif len(s.dropna()) and pd.to_numeric(s.dropna(), errors='coerce').notna().mean() >= .8:
                add(c, 'Posible tipo numérico incorrecto', ~nulls[c])
    duplicates = int(df.duplicated().sum())
    if duplicates: issues.append({'Columna': 'Todas', 'Problema': 'Filas duplicadas', 'Registros': duplicates})
    if keys:
        n = int(df.duplicated(subset=list(keys)).sum())
        if n: issues.append({'Columna': ', '.join(keys), 'Problema': 'Posibles duplicados por clave', 'Registros': n})
    names = [str(c).strip().casefold() for c in df.columns]
    if len(set(names)) < len(names) or any(str(c) != str(c).strip() for c in df.columns):
        issues.append({'Columna': 'Encabezados', 'Problema': 'Nombres repetidos o inconsistentes', 'Registros': len(names)})
    completeness = 1 - nulls.to_numpy().sum()/max(df.size, 1)
    uniqueness = 1 - duplicates/max(len(df), 1)
    consistency = 1 - inconsistent.to_numpy().sum()/max(df.size, 1)
    return {'score': round(100*(.5*completeness+.3*uniqueness+.2*consistency), 1),
            'components': {'Completitud': completeness*100, 'Unicidad': uniqueness*100, 'Consistencia': consistency*100},
            'issues': pd.DataFrame(issues, columns=['Columna', 'Problema', 'Registros'])}
