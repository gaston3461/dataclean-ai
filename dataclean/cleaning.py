import re
import unicodedata
from datetime import datetime, timezone
import pandas as pd
from .profiling import missing
from .quality import outlier_mask

OPERATIONS = ['Eliminar duplicados', 'Eliminar columnas vacías', 'Eliminar filas vacías', 'Recortar espacios',
              'Minúsculas', 'Mayúsculas', 'Estandarizar nombres', 'Convertir a número', 'Convertir a texto',
              'Convertir fechas', 'Reemplazar/unificar categorías', 'Eliminar filas con faltantes',
              'Imputar media', 'Imputar mediana', 'Imputar moda', 'Imputar valor',
              'Eliminar atípicos', 'Limitar atípicos IQR', 'Limitar atípicos (método elegido)']


def transform(df, operation, columns=(), value='', old='', dayfirst=True, method='IQR', iqr_factor=1.5, z_threshold=3.0):
    out = df.copy(deep=True)
    cols = list(columns)
    if operation not in OPERATIONS: raise ValueError('Operación desconocida.')
    if operation not in OPERATIONS[:3] + ['Estandarizar nombres'] and not cols:
        raise ValueError('Seleccioná al menos una columna.')
    if operation == 'Eliminar duplicados': out = out.drop_duplicates(subset=cols or None)
    elif operation == 'Eliminar columnas vacías': out = out.loc[:, ~missing(out).all()]
    elif operation == 'Eliminar filas vacías': out = out.loc[~missing(out).all(axis=1)]
    elif operation == 'Estandarizar nombres':
        names, used = [], set()
        for c in out:
            base = re.sub(r'[^a-z0-9]+', '_', unicodedata.normalize('NFKD', str(c)).encode('ascii', 'ignore').decode().lower()).strip('_') or 'columna'
            name = base; i = 2
            while name in used: name = f'{base}_{i}'; i += 1
            used.add(name); names.append(name)
        out.columns = names
    elif operation == 'Eliminar filas con faltantes': out = out.loc[~missing(out)[cols].any(axis=1)]
    elif operation == 'Eliminar atípicos':
        from .outliers import analyze_outliers
        details = [analyze_outliers(out[c], method, iqr_factor, z_threshold, min_samples=3 if method!='Automático' else 8) for c in cols]
        if any(d['method']=='Omitido' for d in details): raise ValueError('Columna excluida o muestra insuficiente: revisá el diagnóstico de atípicos.')
        masks = [d['mask'] for d in details]
        if len(masks) != len(cols): raise ValueError('Los atípicos requieren columnas numéricas.')
        out = out.loc[~pd.concat(masks, axis=1).any(axis=1)]
    else:
        for c in cols:
            s = out[c]
            if operation in ('Recortar espacios', 'Minúsculas', 'Mayúsculas'):
                fn = {'Recortar espacios': str.strip, 'Minúsculas': str.lower, 'Mayúsculas': str.upper}[operation]
                out[c] = s.map(lambda x: fn(x) if isinstance(x, str) else x)
            elif operation == 'Convertir a número': out[c] = pd.to_numeric(s, errors='coerce')
            elif operation == 'Convertir a texto': out[c] = s.astype('string')
            elif operation == 'Convertir fechas': out[c] = pd.to_datetime(s, errors='coerce', dayfirst=dayfirst, format='mixed')
            elif operation == 'Reemplazar/unificar categorías': out[c] = s.replace(old, value)
            elif operation.startswith('Imputar'):
                clean = s.mask(missing(out)[c])
                if operation in ('Imputar media', 'Imputar mediana'):
                    if not pd.api.types.is_numeric_dtype(s): raise ValueError('Media y mediana requieren números.')
                    fill = clean.mean() if operation == 'Imputar media' else clean.median()
                    clean = clean.astype(float)
                elif operation == 'Imputar moda':
                    modes = clean.mode()
                    if modes.empty: raise ValueError('No existe una moda para esta columna.')
                    fill = modes.iloc[0]
                else:
                    fill = value
                    if pd.api.types.is_numeric_dtype(s): fill = float(value); clean = clean.astype(float)
                    elif pd.api.types.is_datetime64_any_dtype(s): fill = pd.to_datetime(value)
                out[c] = clean.fillna(fill)
            elif operation in ('Limitar atípicos IQR', 'Limitar atípicos (método elegido)'):
                if not pd.api.types.is_numeric_dtype(s): raise ValueError('Seleccioná columnas numéricas.')
                from .outliers import analyze_outliers
                detail = analyze_outliers(s, 'IQR' if operation=='Limitar atípicos IQR' else method, iqr_factor, z_threshold, min_samples=3 if method!='Automático' else 8)
                if detail['method']=='Omitido': raise ValueError(detail['reason'])
                out[c] = s.clip(detail['lower'], detail['upper'])
    return out


def affected(before, after):
    common = before.index.intersection(after.index)
    cols = before.columns.intersection(after.columns)
    changed = pd.Series(False, index=common)
    for c in cols:
        a, b = before.loc[common, c], after.loc[common, c]
        changed |= ~(a.eq(b).fillna(False) | (a.isna() & b.isna()))
    count = len(before.index.difference(after.index)) + int(changed.sum())
    if not before.columns.equals(after.columns): count = max(count, len(before))
    return count


class History:
    def __init__(self, df):
        self._original = df.copy(deep=True)
        self.current = df.copy(deep=True)
        self.records = []
        self._undo = []
        self.revision = 0
    @property
    def original(self): return self._original.copy(deep=True)
    def apply(self, result, operation, columns, metadata=None):
        self.revision += 1
        self._undo.append(self.current.copy(deep=True))
        self.records.append({'fecha_UTC': datetime.now(timezone.utc).isoformat(), 'operación': operation,
                             'columnas': list(columns), 'registros_afectados': affected(self.current, result),
                             'filas_antes': len(self.current), 'filas_después': len(result), 'parámetros':metadata or {}})
        self.current = result.copy(deep=True)
    def undo(self):
        if self._undo:
            self.current = self._undo.pop(); self.records.pop(); self.revision += 1
    def reset(self):
        self.current = self.original; self.records.clear(); self._undo.clear(); self.revision += 1
