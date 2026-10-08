"""Evidencia de relaciones y consolidación con límites previos al merge."""
from difflib import SequenceMatcher
from itertools import combinations
import pandas as pd
from .roles import normalized_name
from .profiling import missing
from .loading import MAX_CELLS

CARDINALITIES = {'Uno a uno':'one_to_one', 'Uno a muchos':'one_to_many',
                 'Muchos a uno':'many_to_one', 'Muchos a muchos':'many_to_many'}
MAX_JOIN_ROWS = 200_000


def type_family(s):
    if pd.api.types.is_datetime64_any_dtype(s): return 'fecha'
    if pd.api.types.is_bool_dtype(s): return 'bool'
    if pd.api.types.is_numeric_dtype(s): return 'número'
    return 'texto'


def canonical_name(name):
    name = normalized_name(name)
    aliases = {'dni':'documento','document':'documento','documento':'documento',
               'idcliente':'clienteid','clienteid':'clienteid',
               'codigoproducto':'productoid','codproducto':'productoid','productoid':'productoid','idproducto':'productoid'}
    return aliases.get(name,name)


def valid_keys(df, keys):
    return ~missing(df)[list(keys)].any(axis=1)


def cardinality(left, right, left_keys, right_keys):
    l = left.loc[valid_keys(left,left_keys), list(left_keys)]
    r = right.loc[valid_keys(right,right_keys), list(right_keys)]
    lu,ru = not l.duplicated().any(),not r.duplicated().any()
    return 'Uno a uno' if lu and ru else 'Uno a muchos' if lu else 'Muchos a uno' if ru else 'Muchos a muchos'


def detect_relations(tables, max_candidates=30):
    candidates=[]
    for (lname,left),(rname,right) in combinations(tables.items(),2):
        # El límite es explícito en la UI y documentación para evitar exploración cuadrática sin límite.
        for lc in list(left.columns)[:60]:
            ls = left.loc[valid_keys(left,[lc]),lc]
            for rc in list(right.columns)[:60]:
                if type_family(left[lc])!=type_family(right[rc]): continue
                name_similarity=SequenceMatcher(None,canonical_name(lc),canonical_name(rc)).ratio()
                if name_similarity<.35: continue
                rs=right.loc[valid_keys(right,[rc]),rc]
                lset,rset=set(ls.unique()),set(rs.unique())
                shared=len(lset & rset)
                if not shared: continue
                coverage=shared/max(min(len(lset),len(rset)),1)
                if coverage<.1: continue
                left_pct=100*ls.isin(rset).sum()/max(len(ls),1)
                right_pct=100*rs.isin(lset).sum()/max(len(rs),1)
                lu,ru=not ls.duplicated().any(),not rs.duplicated().any()
                score=round(100*(.25*name_similarity+.55*coverage+.2*int(lu or ru)),1)
                candidates.append({'Tabla izquierda':lname,'Clave izquierda':lc,'Tabla derecha':rname,'Clave derecha':rc,
                                   'Puntuación':score,'Similitud nombres %':round(name_similarity*100,1),
                                   'Valores distintos compartidos':shared,'Coincidencia filas izquierda %':round(left_pct,1),
                                   'Coincidencia filas derecha %':round(right_pct,1),
                                   'Unicidad izquierda %':round(100*ls.nunique()/max(len(ls),1),1),
                                   'Unicidad derecha %':round(100*rs.nunique()/max(len(rs),1),1),
                                   'Nulos izquierda':int((~valid_keys(left,[lc])).sum()),
                                   'Nulos derecha':int((~valid_keys(right,[rc])).sum()),
                                   'Duplicados clave izquierda':int(ls.duplicated().sum()),
                                   'Duplicados clave derecha':int(rs.duplicated().sum()),
                                   'Cardinalidad':cardinality(left,right,[lc],[rc]),
                                   'PK/FK probable':'Izquierda candidata PK → derecha FK' if lu and not ru else
                                   'Derecha candidata PK → izquierda FK' if ru and not lu else 'Revisar reglas de negocio',
                                   'Límite':'Coincidencia observada; no demuestra equivalencia semántica ni integridad futura.'})
    return pd.DataFrame(sorted(candidates,key=lambda item:item['Puntuación'],reverse=True)[:max_candidates])


def compatible_concat(left,right):
    if set(left.columns)!=set(right.columns): return False
    return all(type_family(left[c])==type_family(right[c]) for c in left.columns)


def aggregate_table(df, keys, measures, method='sum'):
    if not keys or not measures or set(keys)&set(measures): raise ValueError('Seleccioná claves y medidas distintas.')
    if method not in ('sum','mean','median','count'): raise ValueError('Agregación inválida.')
    if any(not pd.api.types.is_numeric_dtype(df[c]) for c in measures): raise ValueError('Las medidas deben ser numéricas.')
    return df.groupby(list(keys),dropna=False,as_index=False)[list(measures)].agg(method)


def prepare_concat(left,right,align=False):
    common=set(left.columns)&set(right.columns)
    if any(type_family(left[c])!=type_family(right[c]) for c in common):
        raise ValueError('Tipos incompatibles en columnas comunes. Convertí explícitamente antes de concatenar.')
    if not align and set(left.columns)!=set(right.columns): raise ValueError('Las columnas difieren. Aprobá alinear columnas para apilar con nulos.')
    columns=set(left.columns)|set(right.columns)
    expected=len(left)+len(right)
    if expected>MAX_JOIN_ROWS or expected*len(columns)>MAX_CELLS: raise ValueError('Consolidación supera el límite de filas o celdas.')
    result=pd.concat([left,right],ignore_index=True,sort=False)
    return result, {'Operación':'Concatenación vertical','Filas izquierda':len(left),'Filas derecha':len(right),
                    'Filas previstas':expected,'Filas resultado':len(result),'Columnas alineadas con nulos':not compatible_concat(left,right),
                    'Riesgo':not compatible_concat(left,right),'Advertencia':'Revisar unidades, períodos y duplicados; compatibilidad de esquema no demuestra equivalencia de significado.'}


def prepare_join(left,right,left_keys,right_keys,how='left',expected_cardinality=None,null_policy='keep'):
    left_keys,right_keys=list(left_keys),list(right_keys)
    if how not in ('inner','left','right','outer'): raise ValueError('Tipo de JOIN inválido.')
    if not left_keys or len(left_keys)!=len(right_keys): raise ValueError('Elegí la misma cantidad de claves en ambas tablas.')
    if len(set(left_keys))!=len(left_keys) or len(set(right_keys))!=len(right_keys): raise ValueError('Las claves no pueden repetirse.')
    for lc,rc in zip(left_keys,right_keys):
        if type_family(left[lc])!=type_family(right[rc]): raise ValueError('Claves con tipos incompatibles; convertí explícitamente antes del JOIN.')
    if null_policy not in ('keep','exclude'): raise ValueError('Política de nulos inválida.')
    if '_merge' in left or '_merge' in right: raise ValueError('Renombrá la columna reservada _merge antes del JOIN.')
    lv,rv=valid_keys(left,left_keys),valid_keys(right,right_keys)
    l,r=left.loc[lv].copy(),right.loc[rv].copy()
    labels=[f'k{i}' for i in range(len(left_keys))]
    lc=l[left_keys].copy(); lc.columns=labels
    rc=r[right_keys].copy(); rc.columns=labels
    counts=lc.value_counts().rename('left').to_frame().join(rc.value_counts().rename('right'),how='outer').fillna(0)
    matches=counts[(counts.left>0)&(counts.right>0)]
    matched=sum(int(a)*int(b) for a,b in zip(matches.left,matches.right))
    lonly=int(counts.loc[counts.right==0,'left'].sum()); ronly=int(counts.loc[counts.left==0,'right'].sum())
    ln,rn=int((~lv).sum()),int((~rv).sum())
    expected=matched+(lonly if how in ('left','outer') else 0)+(ronly if how in ('right','outer') else 0)
    if null_policy=='keep': expected+=(ln if how in ('left','outer') else 0)+(rn if how in ('right','outer') else 0)
    if expected>MAX_JOIN_ROWS or expected*(len(left.columns)+len(right.columns)+1)>MAX_CELLS:
        raise ValueError(f'JOIN bloqueado antes de materializar: {expected:,} filas previstas; límite {MAX_JOIN_ROWS:,} y {MAX_CELLS:,} celdas.')
    actual=cardinality(left,right,left_keys,right_keys)
    validate=CARDINALITIES.get(expected_cardinality or actual)
    if validate is None: raise ValueError('Cardinalidad inválida.')
    try:
        result=l.merge(r,left_on=left_keys,right_on=right_keys,how=how,validate=validate,indicator=True,suffixes=('_izq','_der'))
        if null_policy=='keep':
            # Los nulos nunca se emparejan entre sí: semántica SQL, incluyendo claves compuestas parcialmente nulas.
            pieces=[result]
            if how in ('left','outer') and ln:
                pieces.append(left.loc[~lv].merge(r.iloc[:0],left_on=left_keys,right_on=right_keys,how='left',indicator=True,suffixes=('_izq','_der')))
            if how in ('right','outer') and rn:
                pieces.append(l.iloc[:0].merge(right.loc[~rv],left_on=left_keys,right_on=right_keys,how='right',indicator=True,suffixes=('_izq','_der')))
            result=pd.concat(pieces,ignore_index=True)
        if len(result)!=expected: raise ValueError('Expansión inesperada: el resultado difiere de la estimación previa.')
    except pd.errors.MergeError as exc:
        raise ValueError('La cardinalidad declarada no se cumple o los sufijos generan nombres duplicados. Revisá claves y nombres.') from exc
    result['_merge']=result['_merge'].astype('string')
    risk=actual!='Uno a uno' or expected>max(len(left),len(right)) or ln+rn>0
    stats={'Operación':f'{how.upper()} JOIN','Cardinalidad observada':actual,
           'Filas izquierda':len(left),'Filas derecha':len(right),'Filas previstas':expected,'Filas resultado':len(result),
           'Filas izquierda sin coincidencia':lonly+ln,'Filas derecha sin coincidencia':ronly+rn,
           'Claves repetidas izquierda':int(l.duplicated(subset=left_keys).sum()),
           'Claves repetidas derecha':int(r.duplicated(subset=right_keys).sum()),
           'Claves nulas izquierda':ln,'Claves nulas derecha':rn,'Política nulos':null_policy,
           'Factor filas / tabla mayor':round(expected/max(len(left),len(right),1),2),'Riesgo':risk,
           'Advertencia':'Uno a muchos repite atributos de la tabla padre; muchos a muchos puede multiplicar registros. Considerá agregar medidas previamente, usar claves compuestas o mantener el modelo relacional.'}
    return result,stats
