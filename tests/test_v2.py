from io import BytesIO
import numpy as np
import pandas as pd
import pytest
from dataclean.loading import load_workbook
from dataclean.workspace import Workspace
from dataclean.cleaning import transform
from dataclean.exporting import workbook_bytes
from dataclean.relations import (detect_relations, prepare_join, prepare_concat, cardinality,
                                aggregate_table, compatible_concat)
from dataclean.automatic import select_visualizations, render_visualization
from dataclean.outliers import analyze_outliers
from dataclean.roles import roles


def test_workbook_all_sheets_and_empty():
    raw=BytesIO()
    with pd.ExcelWriter(raw,engine='openpyxl') as w:
        pd.DataFrame({'id':[1,1],'nombre':[' A ',' A ']}).to_excel(w,sheet_name='Clientes',index=False)
        pd.DataFrame({'venta':[30]}).to_excel(w,sheet_name='Ventas',index=False)
        pd.DataFrame().to_excel(w,sheet_name='Vacía',index=False)
    tables=load_workbook(raw.getvalue(),'libro.xlsx')
    assert list(tables)==['Clientes','Ventas','Vacía'] and tables['Vacía'].empty
    ws=Workspace()
    keys=[ws.add(df,name,'libro.xlsx') for name,df in tables.items()]
    ws.select(keys[0]); original=ws.datasets[keys[0]].history.original
    ws.datasets[keys[0]].history.apply(transform(original,'Eliminar duplicados'),'Eliminar duplicados',[])
    ws.select(keys[1]); assert len(ws.datasets[keys[1]].history.current)==1
    ws.select(keys[0]); assert len(ws.datasets[keys[0]].history.current)==1
    assert ws.datasets[keys[0]].history.original.equals(original)
    assert ws.datasets[keys[1]].history.records==[]
    ws.datasets[keys[0]].history.undo(); assert len(ws.datasets[keys[0]].history.current)==2
    assert len(ws.summary())==3


def test_relations_alias_evidence():
    left=pd.DataFrame({'DNI':[1,2,3],'id_cliente':[10,20,30]})
    right=pd.DataFrame({'Documento':[1,1,3,None],'Cliente_ID':[10,10,30,30]})
    candidates=detect_relations({'Clientes':left,'Pedidos':right})
    pair=candidates[(candidates['Clave izquierda']=='DNI')&(candidates['Clave derecha']=='Documento')].iloc[0]
    assert pair['Cardinalidad']=='Uno a muchos' and pair['Nulos derecha']==1
    assert pair['Valores distintos compartidos']==2
    assert pair['Unicidad izquierda %']==100
    assert detect_relations({'a':left,'b':pd.DataFrame({'Documento':[100,200]})}).empty


def test_concat_compatible_and_align():
    left=pd.DataFrame({'a':[1],'b':['x']}); right=pd.DataFrame({'b':['y'],'a':[2]})
    result,stats=prepare_concat(left,right)
    assert result.a.tolist()==[1,2] and compatible_concat(left,right)
    assert left.a.tolist()==[1]
    with pytest.raises(ValueError): prepare_concat(left,pd.DataFrame({'a':['texto']}))
    with pytest.raises(ValueError): prepare_concat(left,pd.DataFrame({'a':[3]}))
    result,stats=prepare_concat(left,pd.DataFrame({'a':[3]}),align=True)
    assert pd.isna(result.b.iloc[1]) and stats['Riesgo']


@pytest.mark.parametrize('how,rows',[('inner',2),('left',3),('right',3),('outer',4)])
def test_join_one_to_one(how,rows):
    left=pd.DataFrame({'id':[1,2,3],'a':['a','b','c']})
    right=pd.DataFrame({'id':[2,3,4],'b':[20,30,40]})
    result,stats=prepare_join(left,right,['id'],['id'],how,'Uno a uno')
    assert len(result)==rows and stats['Filas previstas']==rows
    assert stats['Filas izquierda sin coincidencia']==1
    assert len(left)==3 and 'b' not in left


def test_join_cardinality_and_explosion_prevention():
    left=pd.DataFrame({'id':[1,2],'cliente':['a','b']})
    right=pd.DataFrame({'id':[1,1,2],'venta':[5,6,7]})
    result,stats=prepare_join(left,right,['id'],['id'],expected_cardinality='Uno a muchos')
    assert len(result)==3 and stats['Riesgo']
    with pytest.raises(ValueError,match='cardinalidad'): prepare_join(left,right,['id'],['id'],expected_cardinality='Uno a uno')
    many=pd.DataFrame({'id':[1]*500})
    with pytest.raises(ValueError,match='bloqueado antes'): prepare_join(many,many,['id'],['id'])
    small=pd.DataFrame({'id':[1,1]})
    result,stats=prepare_join(small,small,['id'],['id'])
    assert len(result)==4 and stats['Riesgo'] and stats['Cardinalidad observada']=='Muchos a muchos'


@pytest.mark.parametrize('how,expected',[('inner',1),('left',3),('right',3),('outer',5)])
def test_null_keys_never_match(how,expected):
    left=pd.DataFrame({'id':[1,None,None],'v':[1,2,3]})
    right=pd.DataFrame({'id':[1,None,None],'w':[4,5,6]})
    result,stats=prepare_join(left,right,['id'],['id'],how)
    assert len(result)==expected
    assert len(result[result['_merge']=='both'])==1
    assert stats['Claves nulas izquierda']==2
    assert not result.loc[result.id.isna(),['v','w']].notna().all(axis=1).any()
    excluded,_=prepare_join(left,right,['id'],['id'],how,null_policy='exclude')
    assert len(excluded)==1


def test_composite_and_empty_keys():
    left=pd.DataFrame({'id':[1,1,2],'parte':['A',None,'B']})
    right=pd.DataFrame({'id':[1,1,2],'parte':['A',None,'B']})
    result,stats=prepare_join(left,right,['id','parte'],['id','parte'],'outer')
    assert len(result)==4 and len(result[result['_merge']=='both'])==2
    empty=left.iloc[:0]
    result,stats=prepare_join(empty,right,['id'],['id'],'right')
    assert len(result)==3
    with pytest.raises(ValueError): prepare_join(left,right,[],[])
    with pytest.raises(ValueError): prepare_join(left,right,['id'],['parte'])


def test_aggregation_and_derived_preserve_sources():
    left=pd.DataFrame({'id':[1,2]}); right=pd.DataFrame({'id':[1,1,2],'importe':[5,6,7]})
    aggregated=aggregate_table(right,['id'],['importe'],'sum')
    result,stats=prepare_join(left,aggregated,['id'],['id'],expected_cardinality='Uno a uno')
    assert result.importe.tolist()==[11,7] and len(right)==3
    ws=Workspace(); a=ws.add(left,'Clientes'); b=ws.add(right,'Ventas')
    c=ws.add(result,'Consolidado',lineage={'parents':[a,b],'stats':stats})
    ws.datasets[c].history.apply(transform(result,'Eliminar filas con faltantes',['importe']),'limpieza',['importe'])
    assert ws.datasets[b].history.original.equals(right) and ws.datasets[b].history.current.equals(right)
    assert ws.datasets[c].lineage['parents']==[a,b]


def representative():
    rng=np.random.default_rng(17)
    return pd.DataFrame({'cliente_id':np.arange(80),'fecha':pd.date_range('2026-01-01',periods=80),
                         'ciudad':['Córdoba','Rosario']*40,'importe':rng.normal(100,20,80),
                         'cantidad':rng.integers(1,20,80),'DNI':np.arange(80)+10000000})


def test_auto_charts_scoring_and_no_ids():
    df=representative(); original=df.copy(deep=True)
    specs=select_visualizations(df,8)
    assert 4<=len(specs)<=8
    assert len(set(s['key'] for s in specs))==len(specs)
    for spec in specs:
        assert spec['x'] not in ('DNI','cliente_id') and spec['y'] not in ('DNI','cliente_id')
        assert not set(spec['columns'])&{'DNI','cliente_id'}
        assert spec['reason'] and spec['question']
        for dark in (False,True):
            fig,conclusion=render_visualization(df,spec,dark)
            assert fig.data and conclusion and fig.layout.title.text
    assert df.equals(original)
    assert 'time' in [s['kind'] for s in specs]
    assert select_visualizations(pd.DataFrame({'id':[1,2,3]}))==[]
    assert select_visualizations(pd.DataFrame({'valor':[1,1,1]}))==[]


def test_auto_charts_different_datasets_and_inferred_dates():
    categorical=pd.DataFrame({'zona':['A']*10+['B']*8})
    specs=select_visualizations(categorical)
    assert [s['kind'] for s in specs]==['count']
    dates=pd.DataFrame({'fecha':['01/01/2026','02/01/2026','03/01/2026'],'importe':[5.,6.,8.]})
    specs=select_visualizations(dates)
    time=next(s for s in specs if s['kind']=='time')
    assert render_visualization(dates,time)[0].data
    assert roles(dates)['fecha']=='Temporal' and dates.fecha.dtype==object


def test_auto_outlier_selection_thresholds_exclusions():
    normal=pd.Series(np.random.default_rng(7).normal(size=500),name='medida')
    info=analyze_outliers(normal)
    assert info['method']=='Z-score'
    skew=pd.Series(np.random.default_rng(7).exponential(size=500),name='importe')
    assert analyze_outliers(skew)['method']=='IQR'
    extreme=pd.Series([1.,2.,3.,4.,5.,6.,7.,8.,100.],name='importe')
    info=analyze_outliers(extreme)
    assert info['method']=='IQR' and info['count']==1 and info['mask'].iloc[-1]
    assert analyze_outliers(extreme,iqr_factor=100)['count']==0
    assert analyze_outliers(normal,z_threshold=.5)['count']>info['count']
    for s in (normal.rename('DNI'),normal.rename('Código_Producto'),pd.Series([1,2]*40,name='tipo'),pd.Series([2.]*20,name='importe'),pd.Series([1.,2.],name='importe')):
        assert analyze_outliers(s)['method']=='Omitido'
    assert analyze_outliers(normal,exclude=True)['count']==0
    with pytest.raises(ValueError): transform(pd.DataFrame({'DNI':np.arange(100)}),'Eliminar atípicos',['DNI'],method='Automático')


def test_workbook_export_names_metadata_and_safe_values():
    tables={'Ventas/enero':pd.DataFrame({'importe':[12.5],'texto':['=1+1']}),
            'Historial':pd.DataFrame({'id':[1]}),'historial':pd.DataFrame({'id':[2]}),
            'Nombre demasiado largo para una hoja de Excel':pd.DataFrame({'x':[3]})}
    raw=workbook_bytes(tables,{'Ventas/enero':[{'operación':'prueba','columnas':['texto']}]},True)
    with pd.ExcelFile(BytesIO(raw)) as book:
        assert len(book.sheet_names)==6
        assert len(set(s.casefold() for s in book.sheet_names))==6
        assert all(len(s)<=31 and '/' not in s for s in book.sheet_names)
        assert book.parse('Ventas_enero').texto.iloc[0]=="'=1+1"
        assert book.parse('Resumen de calidad').shape[0]==4
    assert tables['Ventas/enero'].texto.iloc[0]=='=1+1'
