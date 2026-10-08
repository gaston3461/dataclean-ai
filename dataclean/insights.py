from .profiling import semantic


def insights(df):
    findings, recommendations, hypotheses = [], [], []
    nums = list(df.select_dtypes(include='number').columns)
    for c in nums:
        s = df[c].dropna()
        if len(s): findings.append(f'{c}: media {s.mean():,.2f}; mínimo {s.min():,.2f}; máximo {s.max():,.2f}.')
        if semantic(df[c]) == 'Importe monetario':
            findings.append(f'{c}: suma observada {s.sum():,.2f} (verificá moneda y granularidad antes de llamarla facturación).')
            recommendations.append(f'Compará {c} por categoría y fecha; el ticket promedio requiere identificar transacciones.')
        if semantic(df[c]) == 'Cantidad': recommendations.append(f'Explorá el ranking de {c}; la rotación necesita ventas y stock promedio del mismo período.')
    for c in df.select_dtypes(include=['object', 'string', 'category']):
        counts = df[c].value_counts()
        if len(counts): findings.append(f'{c}: categoría más frecuente «{counts.index[0]}», {counts.iloc[0]} registros ({counts.iloc[0]/max(len(df),1):.1%}).')
    if len(nums)>1:
        corr = df[nums].corr()
        pairs = [(a,b,corr.loc[a,b]) for i,a in enumerate(nums) for b in nums[i+1:] if abs(corr.loc[a,b]) >= .7]
        for a,b,r in pairs:
            findings.append(f'Correlación de Pearson entre {a} y {b}: {r:.2f}. No implica causalidad.')
            hypotheses.append(f'Investigar factores comunes entre {a} y {b}, muestras pequeñas y valores extremos.')
    recommendations += ['¿Cómo cambia el volumen de registros por período?', '¿Qué categorías concentran los valores y qué segmentos merecen revisión?']
    if any('consulta' in str(c).lower() or 'edad' in str(c).lower() for c in df):
        recommendations.append('Explorá consultas por período o edades si están disponibles; los datos no permiten inferir diagnósticos ausentes.')
    return findings, recommendations, hypotheses
