import numpy as np
import pandas as pd
from .roles import identifier, numeric_category


def analyze_outliers(s, method='Automático', iqr_factor=1.5, z_threshold=3.0, min_samples=8, exclude=False):
    if iqr_factor <= 0 or z_threshold <= 0: raise ValueError('Los umbrales deben ser positivos.')
    mask = pd.Series(False, index=s.index)
    result = {'method': 'Omitido', 'reason': '', 'count': 0, 'percent': 0.0,
              'lower': None, 'upper': None, 'mask': mask, 'valid': 0}
    if exclude or identifier(s): result['reason'] = 'Identificador/código o columna excluida por el usuario.'; return result
    if not pd.api.types.is_numeric_dtype(s) or numeric_category(s):
        result['reason'] = 'No es una medida numérica continua; posible categoría codificada.'; return result
    values = pd.to_numeric(s, errors='coerce').replace([np.inf,-np.inf], np.nan).dropna().astype(float)
    n = len(values); result['valid'] = n
    if n < min_samples or values.nunique() < (3 if method=='Automático' else 2) or values.std(ddof=0) == 0:
        result['reason'] = f'Menos de {min_samples} valores finitos o variabilidad insuficiente.'; return result
    skew, kurt = float(values.skew()), float(values.kurt())
    repeated = 1-values.nunique()/n
    std = values.std(ddof=0)
    extreme = ((values-values.mean()).abs()/std).max()
    approx_normal = n>=30 and abs(skew)<=.5 and abs(kurt)<=1 and repeated<.2 and extreme<=4
    chosen = 'Z-score' if method=='Automático' and approx_normal else 'IQR' if method=='Automático' else method
    if chosen not in ('IQR','Z-score'): raise ValueError('Método desconocido.')
    reason = (f'n={n}; asimetría={skew:.2f}; curtosis excedente={kurt:.2f}; repetición={repeated:.0%}. ' +
              ('Distribución aproximadamente simétrica, muestra suficiente y dispersión válida (heurística, no prueba de normalidad).'
               if chosen=='Z-score' and method=='Automático' else
               'IQR robusto: asimetría, extremos o evidencia insuficiente de normalidad.' if method=='Automático' else 'Método elegido manualmente.'))
    if chosen=='IQR':
        q1,q3 = values.quantile([.25,.75]); span=q3-q1
        if span == 0:
            reason += ' IQR nulo por valores repetidos: revisar extremos con especial cautela.'
        low,high = q1-iqr_factor*span,q3+iqr_factor*span
    else: low,high=values.mean()-z_threshold*std,values.mean()+z_threshold*std
    numeric = pd.to_numeric(s,errors='coerce')
    mask = ((numeric<low)|(numeric>high)) & numeric.notna() & np.isfinite(numeric)
    result.update(method=chosen, reason=reason, lower=float(low), upper=float(high), mask=mask,
                  count=int(mask.sum()), percent=round(100*mask.sum()/max(len(s),1),2))
    return result


def outlier_table(df, **kwargs):
    rows, details = [], {}
    for c in df.select_dtypes(include='number'):
        detail = analyze_outliers(df[c], **kwargs)
        details[c] = detail
        rows.append({'Columna':c,'Método':detail['method'],'Justificación':detail['reason'],
                     'Atípicos':detail['count'],'Registros %':detail['percent'],
                     'Límite inferior':detail['lower'],'Límite superior':detail['upper']})
    return pd.DataFrame(rows), details
