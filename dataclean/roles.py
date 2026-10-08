"""Roles inferidos conservadores: nunca modifican el dataset."""
import re
import unicodedata
import numpy as np
import pandas as pd
from .profiling import semantic


def normalized_name(name):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', str(name)).encode('ascii', 'ignore').decode().lower())


def identifier(s):
    name = normalized_name(s.name)
    tokens = re.findall(r'[a-z]+', str(s.name).lower())
    explicit = (name in ('id', 'dni', 'documento', 'document', 'cuit', 'cuil', 'rut', 'zipcode', 'codpostal')
                or 'id' in tokens or name.startswith(('id', 'codigo', 'codproducto', 'codcliente'))
                or name.endswith('id') or 'código' in str(s.name).lower())
    clean = s.dropna()
    sequence = False
    if pd.api.types.is_numeric_dtype(s) and len(clean) >= 8 and clean.is_unique:
        values = clean.to_numpy(dtype=float)
        sequence = bool(np.isfinite(values).all() and np.equal(values, np.floor(values)).all()
                        and (np.diff(values) == 1).all() and semantic(s) == 'Numérica')
    return explicit or sequence


def numeric_category(s):
    if not pd.api.types.is_numeric_dtype(s): return False
    clean = s.dropna()
    return (pd.api.types.is_bool_dtype(s) or
            (len(clean) >= 20 and 1 < clean.nunique() <= 8 and clean.nunique()/len(clean) <= .1
             and semantic(s) == 'Numérica'))


def roles(df):
    result = {}
    for c in df:
        s = df[c]
        if identifier(s): role = 'Identificador'
        elif pd.api.types.is_datetime64_any_dtype(s): role = 'Temporal'
        elif numeric_category(s): role = 'Categoría codificada'
        elif pd.api.types.is_numeric_dtype(s): role = 'Numérica'
        elif semantic(s) == 'Geográfica': role = 'Geográfica'
        elif semantic(s) == 'Posible fecha':
            clean = s.dropna()
            valid = pd.to_datetime(clean, errors='coerce', dayfirst=True, format='mixed')
            role = 'Temporal' if len(clean) and valid.notna().mean() >= .8 else 'Categórica'
        else: role = 'Categórica'
        result[c] = role
    return result
