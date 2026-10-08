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
