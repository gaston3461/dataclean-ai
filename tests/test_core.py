from io import BytesIO
import pandas as pd
import pytest
from dataclean.loading import load, sheets, detect_csv
from dataclean.profiling import profile, missing, date_profile
from dataclean.quality import assess, outlier_mask
from dataclean.cleaning import transform, History, affected
from dataclean.exporting import csv_bytes, excel_bytes, report_html
from dataclean.normalization import recommend
from dataclean.charts import make_chart


def test_csv_windows_regional():
    raw = 'ciudad;importe\nCórdoba;12,50\n'.encode('cp1252')
    assert detect_csv(raw)==('cp1252',';')
    df = load(raw,'a.csv',decimal=',')
    assert df.iloc[0].tolist()==['Córdoba',12.5]


@pytest.mark.parametrize('raw,name', [(b'','a.csv'),(b'   ','a.xlsx'),(b'a,b\n','a.csv'),(b'broken','a.xlsx'),(b'a\n1','a.txt')])
def test_invalid(raw,name):
    with pytest.raises(ValueError): load(raw,name)


def test_excel_sheets():
    raw = BytesIO()
    with pd.ExcelWriter(raw,engine='openpyxl') as writer:
        pd.DataFrame({'a':[1]}).to_excel(writer,sheet_name='Primera',index=False)
        pd.DataFrame({'b':[2]}).to_excel(writer,sheet_name='Segunda',index=False)
    assert sheets(raw.getvalue(),'a.xlsx')==['Primera','Segunda']
    assert load(raw.getvalue(),'a.xlsx',sheet='Segunda').iloc[0,0]==2


def test_quality_missing_duplicates():
    df = pd.DataFrame({'a':[' x ','X','X',' '], 'fecha':['01/01/2026','inválida','inválida',None]})
    q = assess(df)
    assert missing(df).sum().sum()==2
    assert df.duplicated().sum()==1
    assert 0<=q['score']<100
    assert 'Fechas inválidas / tipo temporal pendiente' in q['issues'].Problema.tolist()
    assert len(profile(df))==2
    assert date_profile(df).iloc[0]['Válidas']==1


def test_transform_and_history():
    original = pd.DataFrame({' Texto ':[' A ',' A ',None], 'n':['1','1','inválido']})
    history = History(original)
    result = transform(history.current,'Recortar espacios',[' Texto '])
    assert affected(original,result)==2
    history.apply(result,'Recortar espacios',[' Texto '])
    result.iloc[0,0]='alterado'
    assert history.current.iloc[0,0]=='A'
    assert history.original.equals(original)
    history.undo(); assert history.current.equals(original)
    history.apply(transform(original,'Eliminar duplicados'),'Eliminar duplicados',[])
    assert len(history.current)==2
    history.reset(); assert history.current.equals(original) and not history.records


def test_conversion_dates_and_imputation():
    df = pd.DataFrame({'n':['1','bad'], 'fecha':['31/12/2025','bad']})
    result = transform(df,'Convertir a número',['n'])
    assert result.n.iloc[0]==1 and pd.isna(result.n.iloc[1])
    result = transform(result,'Imputar media',['n'])
    assert result.n.tolist()==[1,1]
    result = transform(result,'Convertir fechas',['fecha'])
    assert result.fecha.iloc[0]==pd.Timestamp('2025-12-31') and pd.isna(result.fecha.iloc[1])


def test_names_and_empty_operations():
    df = pd.DataFrame({'Á':[1,None], 'a':[2,None], 'vacía':[None,None]})
    result = transform(df,'Estandarizar nombres')
    assert list(result)==['a','a_2','vacia']
    assert len(transform(df,'Eliminar filas vacías'))==1
    assert 'vacía' not in transform(df,'Eliminar columnas vacías')


def test_outliers_and_ranges():
    df = pd.DataFrame({'n':[1,1,1,1,100]})
    assert outlier_mask(df.n).sum()==1
    assert len(transform(df,'Eliminar atípicos',['n']))==4
    assert transform(df,'Limitar atípicos IQR',['n']).n.max()==1
    assert 'Fuera de rango indicado' in assess(df,ranges={'n':(0,10)})['issues'].Problema.tolist()


def test_exports_safety():
    df = pd.DataFrame({'texto':['=1+1','<script>alert(1)</script>'], 'n':[1,2]})
    csv = csv_bytes(df)
    assert csv.startswith(b'\xef\xbb\xbf') and "'=1+1" in csv.decode('utf-8-sig')
    excel = load(excel_bytes(df),'export.xlsx')
    assert excel.texto.iloc[0]=="'=1+1"
    html = report_html(df,[]).decode()
    assert '<script>alert' not in html and '&lt;script&gt;' in html
    assert df.texto.iloc[0]=='=1+1'


def test_normalization_and_chart():
    df = pd.DataFrame({'id':[1,1,2], 'ciudad':['A','A','B'], 'n':[2,3,4]})
    notes, proposals = recommend(df,['id'],[('id','ciudad')])
    assert len(proposals[0]['tabla'])==2
    assert len(make_chart(df,'Columnas','ciudad','n','Suma').data)==1
    notes, proposals = recommend(df,[],[('ciudad','n')])
    assert not proposals and any('contradicen' in note for note in notes)


def test_xls_fixture():
    from pathlib import Path
    raw = (Path(__file__).parent/'fixtures/ejemplo.xls').read_bytes()
    assert sheets(raw,'a.xls') == ['Datos']
    assert load(raw,'a.xls').iloc[0,0] == 12.5


def test_csv_tabs_and_dates():
    result = load(b'fecha\tn\n31/12/2025\t1\n','a.csv', dates=['fecha'])
    assert result.fecha.iloc[0] == pd.Timestamp('2025-12-31')


def test_size_and_zip_limits():
    import zipfile
    from dataclean.loading import MAX_BYTES
    with pytest.raises(ValueError,match='20 MB'): load(b'a'*(MAX_BYTES+1),'a.csv')
    raw = BytesIO()
    with zipfile.ZipFile(raw,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('oversized',b'0'*(101*1024*1024))
    with pytest.raises(ValueError,match='100 MB'): load(raw.getvalue(),'a.xlsx')
    with pytest.raises(ValueError,match='100 MB'): sheets(raw.getvalue(),'a.xlsx')
