import pandas as pd


def recommend(df, keys=(), dependencies=()):
    notes = ['La estandarización de textos y tipos es distinta de la normalización relacional.',
             'Las muestras no demuestran dependencias funcionales. Confirmá reglas de negocio antes de evaluar 1FN, 2FN o 3FN.']
    candidates = [c for c in df if df[c].notna().all() and df[c].is_unique]
    notes.append('Claves candidatas observadas (requieren validación de negocio): ' + (', '.join(map(str, candidates)) or 'ninguna'))
    repeated = [c for c in df if df[c].astype(str).str.contains(r'[,;|]', regex=True).any()]
    if repeated: notes.append('Revisar valores multivaluados para 1FN: ' + ', '.join(repeated))
    proposals = []
    for determinant, dependent in dependencies:
        if determinant == dependent: continue
        conflicts = df.groupby(determinant, dropna=False)[dependent].nunique(dropna=False).gt(1).sum()
        if conflicts:
            notes.append(f'{determinant} → {dependent}: {conflicts} grupos contradicen la dependencia indicada.')
        else:
            notes.append(f'{determinant} → {dependent}: compatible con la muestra; verificar que sea una regla permanente.')
            table = df[[determinant, dependent]].drop_duplicates()
            if table[determinant].isna().any():
                notes.append(f'{determinant} contiene nulos: no puede ser clave primaria todavía.')
            proposals.append({'nombre': f'dim_{determinant}', 'tabla': table,
                              'relación': f'PK candidata: {determinant}; FK propuesta en tabla principal: {determinant}. Retirar {dependent} solo tras validar la dependencia.'})
    if len(keys)>1: notes.append('2FN: verificá si un atributo depende solo de una parte de la clave compuesta.')
    if dependencies: notes.append('3FN: revisá dependencias transitivas entre atributos que no sean clave.')
    return notes, proposals
