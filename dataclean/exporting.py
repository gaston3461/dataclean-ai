from io import BytesIO
import html
import json
import pandas as pd
from .profiling import profile, statistics
from .quality import assess


def safe_frame(df):
    out = df.copy()
    # Neutralizar fórmulas al abrir archivos exportados en hojas de cálculo.
    def safe(x):
        if isinstance(x, str) and x.lstrip().startswith(('=', '+', '-', '@')): return "'" + x
        return x
    for c in out: out[c] = out[c].map(safe)
    out.columns = [safe(str(c)) for c in out.columns]
    return out


def csv_bytes(df, sep=';', encoding='utf-8-sig', decimal=','):
    return safe_frame(df).to_csv(index=False, sep=sep, decimal=decimal).encode(encoding)


def excel_bytes(df):
    out = BytesIO()
    clean = safe_frame(df)
    for c in clean:
        if isinstance(clean[c].dtype, pd.DatetimeTZDtype): clean[c] = clean[c].dt.tz_localize(None)
    with pd.ExcelWriter(out, engine='openpyxl') as writer: clean.to_excel(writer, index=False, sheet_name='Datos')
    return out.getvalue()


def report_html(df, records):
    quality = assess(df)
    body = f'<h1>DataClean AI — by Sánchez Gastón</h1><p>Índice orientativo: {quality["score"]}/100. No es una certificación.</p>'
    body += '<p>Fórmula: 50% completitud + 30% unicidad + 20% consistencia. Los atípicos no penalizan.</p>'
    body += profile(df).to_html(index=False, escape=True) + quality['issues'].to_html(index=False, escape=True)
    body += statistics(df).to_html(escape=True) + '<pre>'+html.escape(json.dumps(records, ensure_ascii=False, indent=2))+'</pre>'
    return ('<!doctype html><html lang="es"><meta charset="utf-8"><title>Informe DataClean AI</title><body>'+body+'</body></html>').encode('utf-8')
