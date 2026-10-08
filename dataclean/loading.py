import csv
import zipfile
from io import BytesIO
from pathlib import Path
import pandas as pd

MAX_BYTES = 20 * 1024 * 1024
MAX_CELLS = 2_000_000


def detect_csv(raw):
    for encoding in ('utf-8-sig', 'utf-8', 'cp1252', 'latin1'):
        try:
            text = raw.decode(encoding)
            try:
                sep = csv.Sniffer().sniff(text[:8192], delimiters=',;\t|').delimiter
            except csv.Error:
                sep = ','
            return encoding, sep
        except UnicodeDecodeError:
            continue
    raise ValueError('No se pudo detectar la codificación.')


def sheets(raw, name):
    validate(raw)
    if Path(name).suffix.lower() == '.xlsx':
        try:
            with zipfile.ZipFile(BytesIO(raw)) as archive:
                if sum(item.file_size for item in archive.infolist()) > 100 * 1024 * 1024:
                    raise ValueError('Excel supera 100 MB de contenido descomprimido.')
        except zipfile.BadZipFile as exc:
            raise ValueError('Excel dañado o incompatible.') from exc
    engine = 'xlrd' if Path(name).suffix.lower() == '.xls' else 'openpyxl'
    try:
        return pd.ExcelFile(BytesIO(raw), engine=engine).sheet_names
    except Exception as exc:
        raise ValueError('Excel dañado o incompatible.') from exc


def validate(raw):
    if not raw or not raw.strip():
        raise ValueError('El archivo está vacío.')
    if len(raw) > MAX_BYTES:
        raise ValueError('El archivo supera el límite de 20 MB.')


def load(raw, name, sheet=0, encoding=None, sep=None, decimal='.', thousands=None, dates=(), dayfirst=True):
    validate(raw)
    suffix = Path(name).suffix.lower()
    try:
        if suffix == '.csv':
            enc, delimiter = detect_csv(raw)
            df = pd.read_csv(BytesIO(raw), encoding=encoding or enc, sep=sep or delimiter,
                             decimal=decimal, thousands=thousands)
        elif suffix in ('.xlsx', '.xls'):
            if suffix == '.xlsx':
                with zipfile.ZipFile(BytesIO(raw)) as archive:
                    if sum(item.file_size for item in archive.infolist()) > 100 * 1024 * 1024:
                        raise ValueError('Excel supera 100 MB de contenido descomprimido.')
            df = pd.read_excel(BytesIO(raw), sheet_name=sheet,
                               engine='xlrd' if suffix == '.xls' else 'openpyxl',
                               decimal=decimal, thousands=thousands)
        else:
            raise ValueError('Formato incompatible. Usá CSV, XLSX o XLS.')
        if df.empty or not len(df.columns):
            raise ValueError('El archivo no contiene registros.')
        if df.size > MAX_CELLS:
            raise ValueError('El dataset supera el límite de dos millones de celdas.')
        for col in dates:
            df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=dayfirst, format='mixed')
        return df
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('No se pudo leer el archivo. Revisá formato, hoja, separador y codificación.') from exc


def load_workbook(raw, name, decimal='.', thousands=None):
    """Carga atómica de todas las hojas, incluidas hojas sin registros."""
    sheet_names = sheets(raw, name)  # valida tamaño y expansión antes de abrir
    if len(sheet_names) > 40:
        raise ValueError('El libro supera el máximo de 40 hojas.')
    engine = 'xlrd' if Path(name).suffix.lower() == '.xls' else 'openpyxl'
    result, total = {}, 0
    try:
        with pd.ExcelFile(BytesIO(raw), engine=engine) as book:
            for sheet in sheet_names:
                df = book.parse(sheet, decimal=decimal, thousands=thousands)
                total += df.size
                if total > MAX_CELLS:
                    raise ValueError('El libro supera dos millones de celdas entre todas las hojas.')
                result[sheet] = df
        return result
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('No se pudieron leer todas las hojas del libro.') from exc
