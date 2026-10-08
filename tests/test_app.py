from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_pages_and_approval_flow():
    at = AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    assert not at.exception
    next(b for b in at.button if b.label=='Usar dataset ficticio de ejemplo').click().run()
    assert not at.exception
    for page in ['Resumen del dataset','Calidad de datos','Análisis e insights','Visualizaciones','Comparación','Exportación','Acerca de']:
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, (page, at.exception)
    at.sidebar.radio[0].set_value('Limpieza y normalización').run()
    next(b for b in at.button if b.label=='Preparar vista previa').click().run()
    assert not at.exception
    assert len(at.session_state['history'].current)==8
    assert next(b for b in at.button if b.label=='Aplicar').disabled
    next(c for c in at.checkbox if c.label.startswith('Revisé')).check().run()
    next(b for b in at.button if b.label=='Aplicar').click().run()
    assert not at.exception
    assert len(at.session_state['history'].current)==7
    next(b for b in at.button if b.label=='Deshacer').click().run()
    assert len(at.session_state['history'].current)==8
    at.sidebar.selectbox[0].set_value('Oscuro').run()
    assert not at.exception and len(at.session_state['history'].current)==8


def test_v2_independent_sheets_and_consolidation_approval():
    import pandas as pd
    from dataclean.workspace import Workspace
    ws=Workspace()
    a=ws.add(pd.DataFrame({'id':[1,1,2],'nombre':[' A ',' A ','B']}),'Clientes')
    b=ws.add(pd.DataFrame({'id':[1,2],'importe':[10,20]}),'Ventas')
    ws.select(a)
    at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30)
    at.session_state['workspace']=ws
    at.run()
    assert not at.exception
    at.sidebar.radio[0].set_value('Limpieza y normalización').run()
    next(button for button in at.button if button.label=='Preparar vista previa').click().run()
    next(c for c in at.checkbox if c.label.startswith('Revisé la vista')).check().run()
    next(button for button in at.button if button.label=='Aplicar').click().run()
    assert len(ws.datasets[a].history.current)==2
    selector=next(s for s in at.sidebar.selectbox if s.label=='Dataset activo')
    selector.set_value(b).run()
    assert at.session_state['history'] is ws.datasets[b].history
    assert not ws.datasets[b].history.records
    selector=next(s for s in at.sidebar.selectbox if s.label=='Dataset activo')
    selector.set_value(a).run()
    assert len(at.session_state['history'].current)==2 and ws.datasets[a].history.original.shape[0]==3
    at.sidebar.radio[0].set_value('Relaciones y consolidación').run()
    assert not at.exception
    next(button for button in at.button if button.label=='Analizar relaciones').click().run()
    assert not at.exception and not at.session_state['relationships']['table'].empty
    next(r for r in at.radio if r.label=='Operación de consolidación').set_value('JOIN horizontal').run()
    next(s for s in at.multiselect if s.label.startswith('Claves izquierda')).set_value(['id']).run()
    next(s for s in at.multiselect if s.label.startswith('Claves derecha')).set_value(['id']).run()
    next(button for button in at.button if button.label=='Preparar consolidación').click().run()
    assert not at.exception
    assert next(button for button in at.button if button.label=='Crear dataset derivado').disabled
    next(c for c in at.checkbox if c.label.startswith('Revisé y apruebo')).check().run()
    next(button for button in at.button if button.label=='Crear dataset derivado').click().run()
    assert not at.exception
    assert len(ws.datasets)==3 and ws.datasets[ws.active].lineage
    assert len(ws.datasets[a].history.current)==2 and len(ws.datasets[b].history.current)==2
    at.sidebar.radio[0].set_value('Dashboard automático').run()
    assert not at.exception
    at.sidebar.radio[0].set_value('Exportación').run()
    assert not at.exception


def test_v2_many_to_many_needs_extra_approval_and_stale_preview_blocked():
    import pandas as pd
    from dataclean.workspace import Workspace
    ws=Workspace()
    a=ws.add(pd.DataFrame({'id':[1,1],'n':[2,3]}),'A')
    b=ws.add(pd.DataFrame({'id':[1,1],'m':[4,5]}),'B')
    at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30)
    at.session_state['workspace']=ws
    at.run()
    at.sidebar.radio[0].set_value('Relaciones y consolidación').run()
    next(r for r in at.radio if r.label=='Operación de consolidación').set_value('JOIN horizontal').run()
    next(s for s in at.multiselect if s.label.startswith('Claves izquierda')).set_value(['id']).run()
    next(s for s in at.multiselect if s.label.startswith('Claves derecha')).set_value(['id']).run()
    next(s for s in at.selectbox if s.label=='Cardinalidad que debe validar Pandas').set_value('Muchos a muchos').run()
    next(button for button in at.button if button.label=='Preparar consolidación').click().run()
    assert not at.exception
    next(c for c in at.checkbox if c.label.startswith('Revisé y apruebo')).check().run()
    assert next(button for button in at.button if button.label=='Crear dataset derivado').disabled
    next(c for c in at.checkbox if c.label.startswith('Entiendo el riesgo')).check().run()
    assert not next(button for button in at.button if button.label=='Crear dataset derivado').disabled
    next(s for s in at.selectbox if s.label=='Tipo de JOIN').set_value('inner').run()
    assert not any(button.label=='Crear dataset derivado' for button in at.button)
    assert len(ws.datasets)==2
