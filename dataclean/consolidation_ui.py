import streamlit as st
import pandas as pd
from .relations import detect_relations, compatible_concat, prepare_concat, prepare_join, cardinality, CARDINALITIES, aggregate_table
from .ui import professional_table


def consolidation_panel(workspace,dark=False):
    datasets=workspace.datasets
    if len(datasets)<2:
        st.info('Importá al menos dos hojas o archivos para detectar relaciones y consolidar.')
        return
    st.write('Compará evidencia entre tablas y prepará un nuevo dataset sin alterar sus fuentes.')
    frames={f'{d.name} · {k}':d.history.current for k,d in datasets.items()}
    with st.expander('Relaciones candidatas entre todas las tablas',expanded=True):
        st.caption('Hasta 60 columnas por tabla y las 30 candidatas mejor puntuadas. La puntuación combina similitud de nombres (25%), cobertura de valores distintos (55%) y unicidad de al menos un lado (20%). No demuestra equivalencia semántica.')
        if st.button('Analizar relaciones',type='primary'):
            st.session_state.relationships={'signature':[(k,d.history.revision) for k,d in datasets.items()], 'table':detect_relations(frames)}
        stored=st.session_state.get('relationships')
        if stored and stored['signature']==[(k,d.history.revision) for k,d in datasets.items()]:
            if stored['table'].empty: st.info('No hay relaciones con evidencia suficiente. Podés indicar claves manualmente.')
            else: professional_table(stored['table'],dark)
        elif stored: st.caption('Las tablas cambiaron; volvé a analizar para actualizar la evidencia.')
    keys=list(datasets)
    a,b=st.columns(2)
    left_key=a.selectbox('Tabla izquierda',keys,format_func=lambda k:f'{datasets[k].name} · {k}')
    right_key=b.selectbox('Tabla derecha',[k for k in keys if k!=left_key],format_func=lambda k:f'{datasets[k].name} · {k}')
    left,right=datasets[left_key].history.current,datasets[right_key].history.current
    if compatible_concat(left,right): st.success('Estructuras compatibles: se puede proponer concatenación vertical. Confirmá que unidades y significado coincidan.')
    else: st.info('Para atributos complementarios, revisá un JOIN. Si se repiten entidades, considerá mantener tablas relacionadas o agregar previamente.')
    operation=st.radio('Operación de consolidación',['Concatenación vertical','JOIN horizontal'],horizontal=True)
    left_keys,right_keys=[],[]; how='left'; expected=None; null_policy='keep'; align=False
    aggregate_left,aggregate_right=False,False; left_measures,right_measures=[],[]; agg_method='sum'
    if operation=='Concatenación vertical':
        align=st.checkbox('Alinear columnas distintas, completando faltantes con nulos')
    else:
        a,b=st.columns(2)
        left_keys=a.multiselect('Claves izquierda (en orden)',list(left.columns))
        right_keys=b.multiselect('Claves derecha (mismo orden)',list(right.columns))
        how=st.selectbox('Tipo de JOIN',['left','inner','right','outer'],format_func=str.upper)
        inferred=cardinality(left,right,left_keys,right_keys) if left_keys and len(left_keys)==len(right_keys) else None
        if inferred: st.caption(f'Cardinalidad observada antes de agregar: {inferred}. No implica una regla permanente de negocio.')
        expected=st.selectbox('Cardinalidad que debe validar Pandas',list(CARDINALITIES),index=list(CARDINALITIES).index(inferred) if inferred else 0)
        null_choice=st.selectbox('Claves nulas',['Conservar sin emparejar (semántica SQL)','Excluir registros con claves nulas'])
        null_policy='keep' if null_choice.startswith('Conservar') else 'exclude'
        with st.expander('Agregación previa para evitar multiplicación'):
            st.caption('La agregación crea una vista temporal y conserva las fuentes. Retiene solo claves y medidas seleccionadas. Revisá la pérdida de detalle antes de aprobar.')
            agg_method=st.selectbox('Método de agregación',['sum','mean','median','count'],format_func=lambda v:{'sum':'Suma','mean':'Media','median':'Mediana','count':'Conteo no nulo'}[v])
            aggregate_left=st.checkbox('Agregar tabla izquierda antes del JOIN')
            left_measures=st.multiselect('Medidas izquierda',list(left.select_dtypes(include='number').columns))
            aggregate_right=st.checkbox('Agregar tabla derecha antes del JOIN')
            right_measures=st.multiselect('Medidas derecha',list(right.select_dtypes(include='number').columns))
    signature=(left_key,right_key,datasets[left_key].history.revision,datasets[right_key].history.revision,
               operation,tuple(left_keys),tuple(right_keys),how,expected,null_policy,align,
               aggregate_left,aggregate_right,tuple(left_measures),tuple(right_measures),agg_method)
    if st.button('Preparar consolidación'):
        st.session_state.approve_consolidation=False
        st.session_state.confirm_join_risk=False
        st.session_state.pop('consolidation_preview',None)
        try:
            l=aggregate_table(left,left_keys,left_measures,agg_method) if aggregate_left else left
            r=aggregate_table(right,right_keys,right_measures,agg_method) if aggregate_right else right
            if operation=='Concatenación vertical': result,stats=prepare_concat(l,r,align)
            else: result,stats=prepare_join(l,r,left_keys,right_keys,how,expected,null_policy)
            stats['Agregación previa izquierda']=aggregate_left; stats['Agregación previa derecha']=aggregate_right
            stats['Filas fuentes originales']=len(left)+len(right)
            stats['Riesgo']=stats['Riesgo'] or aggregate_left or aggregate_right or null_policy=='exclude'
            st.session_state.consolidation_preview={'df':result,'stats':stats,'signature':signature,
                'parents':[left_key,right_key],'keys':{'left':left_keys,'right':right_keys}}
        except (ValueError,TypeError,KeyError) as exc: st.error(f'Consolidación no preparada: {exc}')
    pending=st.session_state.get('consolidation_preview')
    if pending and pending['signature']!=signature:
        st.info('Cambió la configuración o una fuente. Prepará una nueva vista previa para aprobarla.')
        return
    if pending:
        st.subheader('Revisión previa')
        professional_table(pd.DataFrame({'Indicador':list(pending['stats']),'Valor':list(map(str,pending['stats'].values()))}),dark)
        st.write(f'Fuentes: {datasets[left_key].name} → {datasets[right_key].name}; claves: {left_keys} ↔ {right_keys}')
        professional_table(pending['df'].head(25),dark)
        st.warning(pending['stats']['Advertencia'])
        if pending['stats']['Riesgo']:
            st.warning('Esta operación puede repetir atributos, excluir registros o perder detalle. Una tabla plana puede duplicar sumas. Revisá también la alternativa de mantener un modelo relacional.')
            st.checkbox('Entiendo el riesgo de multiplicación, nulos y pérdida de detalle',key='confirm_join_risk')
        st.checkbox('Revisé y apruebo crear el dataset consolidado',key='approve_consolidation')
        name=st.text_input('Nombre del nuevo dataset',key='derived_name')
        permitted=st.session_state.approve_consolidation and (not pending['stats']['Riesgo'] or st.session_state.confirm_join_risk)
        a,b=st.columns(2)
        if a.button('Crear dataset derivado',disabled=not permitted,type='primary'):
            try:
                lineage={'parents':pending['parents'],'keys':pending['keys'],'operation':pending['stats']}
                workspace.add(pending['df'],name.strip() or 'Consolidado','Consolidación asistida',lineage=lineage)
                st.session_state.pop('consolidation_preview'); st.session_state.pop('preview',None)
                st.rerun()
            except ValueError as exc: st.error(str(exc))
        if b.button('Cancelar consolidación'):
            st.session_state.pop('consolidation_preview'); st.rerun()
