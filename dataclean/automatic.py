"""Selección puntuable de visualizaciones; cálculos separados de renderizado."""
import numpy as np
import pandas as pd
import plotly.express as px
from .roles import roles
from .profiling import semantic


def analysis_frame(df):
    frame=df.copy()
    inferred=roles(df)
    for c,role in inferred.items():
        if role=='Temporal' and not pd.api.types.is_datetime64_any_dtype(frame[c]):
            frame[c]=pd.to_datetime(frame[c],errors='coerce',dayfirst=True,format='mixed')
        if role=='Numérica': frame[c]=frame[c].replace([np.inf,-np.inf],np.nan)
    return frame,inferred


def select_visualizations(df, limit=6):
    limit=max(1,min(int(limit),8))
    frame,inferred=analysis_frame(df)
    nums=[c for c,r in inferred.items() if r=='Numérica' and frame[c].notna().sum()>=3 and frame[c].nunique()>1]
    cats=[c for c,r in inferred.items() if r in ('Categórica','Geográfica','Categoría codificada')
          and 2<=frame[c].nunique()<=50 and frame[c].nunique()<max(len(frame)*.8,3)]
    dates=[c for c,r in inferred.items() if r=='Temporal' and frame[c].nunique()>=2]
    candidates=[]
    def add(kind,x=None,y=None,score=0,reason='',question='',columns=None):
        candidates.append({'kind':kind,'x':x,'y':y,'score':round(score,1),'reason':reason,'question':question,
                           'columns':columns or [], 'key':f'{kind}:{x}:{y}',
                           'title':{'hist':'Distribución','time':'Evolución temporal','bars':'Comparación por categoría',
                                    'count':'Frecuencia de categorías','scatter':'Asociación observada','box':'Distribución por grupo',
                                    'corr':'Correlaciones numéricas'}[kind]+f' · {y or x or "medidas"}'})
    for c in nums:
        valid=frame[c].notna().mean()
        add('hist',c,score=65+10*valid,reason=f'Medida con {frame[c].nunique()} valores distintos; permite ver dispersión y extremos.',question=f'¿Cómo se distribuye {c}?')
    for d in dates:
        for n in nums[:3]:
            valid=frame[[d,n]].dropna()
            if len(valid)>=3:
                add('time',d,n,score=90+5*len(valid)/max(len(frame),1),reason='Fecha reconocida y medida disponible; orden temporal válido.',question=f'¿Cómo evoluciona {n} a lo largo del tiempo?')
    for c in cats:
        add('count',c,score=68+10*(1-frame[c].isna().mean()),reason=f'{frame[c].nunique()} categorías observadas; se muestran las 15 más frecuentes.',question=f'¿Qué categorías de {c} concentran registros?')
        for n in nums[:3]:
            valid=frame[[c,n]].dropna()
            if len(valid)<3: continue
            group=valid.groupby(c)[n].mean()
            if len(group)>=2:
                add('bars',c,n,score=85+5*(semantic(frame[n]) in ('Cantidad','Importe monetario')),reason='Grupos comparables y medida numérica. Ordenado por valor agregado.',question=f'¿Qué grupos de {c} tienen mayor {n}?')
            if valid.groupby(c).size().ge(3).sum()>=2:
                add('box',c,n,score=79,reason='Al menos dos grupos con tres observaciones; compara variabilidad además del promedio.',question=f'¿Cómo cambia la dispersión de {n} entre grupos?')
    if len(nums)>=2:
        selected=nums[:12]
        corr=frame[selected].corr(min_periods=5)
        if corr.notna().to_numpy().sum()>len(selected):
            add('corr',score=81,reason='Medidas variables, sin identificadores ni categorías codificadas; Pearson usa pares válidos (mínimo cinco).',question='¿Qué medidas presentan asociaciones lineales?',columns=selected)
        for i,a in enumerate(selected):
            for b in selected[i+1:]:
                valid=frame[[a,b]].dropna()
                if len(valid)<8: continue
                r=valid[a].corr(valid[b])
                if pd.notna(r) and abs(r)>=.35:
                    add('scatter',a,b,score=77+10*abs(r),reason=f'Pearson r={r:.2f}, {len(valid)} pares válidos. Asociación exploratoria, sin afirmar significancia ni causalidad.',question=f'¿Cómo se relacionan {a} y {b} y dónde están los extremos?')
    # Diversidad: máximo dos por familia, luego completar con candidatos si hay menos de cuatro.
    ranked=sorted(candidates,key=lambda c:c['score'],reverse=True)
    chosen=[]; families={}
    for spec in ranked:
        if families.get(spec['kind'],0)>=2: continue
        chosen.append(spec); families[spec['kind']]=families.get(spec['kind'],0)+1
        if len(chosen)==limit: break
    if len(chosen)<min(4,limit):
        for spec in ranked:
            if spec not in chosen: chosen.append(spec)
            if len(chosen)>=min(4,limit): break
    return chosen


def render_visualization(df,spec,dark=False):
    frame,_=analysis_frame(df)
    kind,x,y=spec['kind'],spec['x'],spec['y']
    conclusion=''
    if frame.empty: raise ValueError('El filtro no contiene registros.')
    if kind=='hist':
        data=frame[[x]].dropna()
        if data.empty: raise ValueError('Sin medidas válidas.')
        fig=px.histogram(data,x=x,nbins=30,labels={x:str(x)},color_discrete_sequence=['#2563EB'])
        conclusion=f'{len(data):,} valores válidos; mediana {data[x].median():,.2f}, rango {data[x].min():,.2f} a {data[x].max():,.2f}.'
    elif kind=='time':
        valid=frame[[x,y]].dropna().copy()
        if valid.empty: raise ValueError('Sin pares fecha/medida válidos.')
        span=valid[x].max()-valid[x].min()
        frequency='MS' if span.days>90 else 'D'
        reducer='sum' if semantic(frame[y]) in ('Cantidad','Importe monetario') else 'mean'
        grouped=valid.set_index(x)[y].resample(frequency).agg(reducer,min_count=1) if reducer=='sum' else valid.set_index(x)[y].resample(frequency).mean()
        data=grouped.dropna().reset_index()
        fig=px.line(data,x=x,y=y,markers=True,labels={x:'Período',y:f'{y} ({"suma" if reducer=="sum" else "media"})'})
        first,last=data[y].iloc[0],data[y].iloc[-1]
        variation=f' Variación entre extremos observados: {(last-first)/abs(first)*100:.1f}%.' if first!=0 else ' Variación porcentual no calculable: el primer valor es cero.'
        conclusion=f'{len(valid)} pares válidos, agregación {"mensual" if frequency=="MS" else "diaria"} por {"suma" if reducer=="sum" else "media"}.{variation} Los períodos sin observaciones se omiten; no prueba causalidad.'
    elif kind in ('bars','count'):
        if kind=='count':
            data=frame[x].value_counts().head(15).rename_axis(x).reset_index(name='Registros'); measure='Registros'
        else:
            reducer='sum' if semantic(frame[y]) in ('Cantidad','Importe monetario') else 'mean'
            data=frame.dropna(subset=[x,y]).groupby(x)[y].agg(reducer).sort_values(ascending=False).head(15).reset_index(); measure=y
        if data.empty: raise ValueError('Sin categorías válidas.')
        fig=px.bar(data.sort_values(measure),x=measure,y=x,orientation='h',labels={measure:f'{measure}'+(' (suma)' if kind=='bars' and reducer=='sum' else ' (media)' if kind=='bars' else '')})
        conclusion=f'Entre las categorías observadas, «{data.iloc[0][x]}» presenta el mayor valor agregado: {data.iloc[0][measure]:,.2f}. Se muestran hasta 15 categorías; revisar unidades y tamaños de grupo.'
    elif kind in ('scatter','box'):
        data=frame[[x,y]].dropna()
        if data.empty: raise ValueError('Sin pares válidos.')
        sampled=data.sample(n=min(5000,len(data)),random_state=17)
        if kind=='scatter':
            fig=px.scatter(sampled,x=x,y=y,opacity=.65)
            r=data[x].corr(data[y]); conclusion=f'{len(data)} pares válidos; Pearson r={r:.2f}. No implica causalidad.'
        else:
            top=data[x].value_counts().head(12).index; sampled=data[data[x].isin(top)]
            sampled=sampled.sample(n=min(5000,len(sampled)),random_state=17)
            fig=px.box(sampled,x=x,y=y,points=False)
            medians=data.groupby(x)[y].median(); conclusion=f'{len(medians)} grupos válidos; medianas entre {medians.min():,.2f} y {medians.max():,.2f}. Hasta 12 grupos visibles.'
        if len(sampled)<len(data): conclusion+=' Gráfico limitado a una muestra reproducible de hasta 5000 puntos; cálculos sobre todos los registros filtrados.'
    else:
        cols=spec['columns']; corr=frame[cols].corr(min_periods=5)
        fig=px.imshow(corr,text_auto='.2f',color_continuous_scale='RdBu',zmin=-1,zmax=1,labels={'color':'Pearson r'})
        conclusion=f'{len(cols)} medidas, sin identificadores. Pares con menos de cinco observaciones o sin variación no tienen correlación calculable. No implica causalidad.'
    if kind!='corr':
        fig.update_traces(marker_color='#14B8A6' if kind in ('count','time') else '#2563EB')
    if kind=='time': fig.update_traces(line_color='#14B8A6')
    fig.update_layout(template='plotly_dark' if dark else 'plotly_white',title=spec['title'],
                      height=360,margin=dict(l=15,r=15,t=60,b=20),font=dict(family='Inter, Arial',size=12,color='#E6EDF8' if dark else '#14243B'),
                      paper_bgcolor='#111C30' if dark else '#FFFFFF',plot_bgcolor='#111C30' if dark else '#FFFFFF',
                      colorway=['#2563EB','#14B8A6','#8B5CF6','#F59E0B'])
    fig.update_xaxes(showgrid=True,gridcolor='#24324A' if dark else '#EDF2F7')
    fig.update_yaxes(showgrid=True,gridcolor='#24324A' if dark else '#EDF2F7')
    return fig,conclusion
