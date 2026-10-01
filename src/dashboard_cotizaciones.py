from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

from src.pipeline_governance import apply_forecast_governance, forecast_summary

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'

st.set_page_config(page_title='SIC-BA Cotizaciones', layout='wide')
st.title('SIC-BA | Pipeline Comercial')
st.caption('Separación estricta entre sugerencias, oportunidades y forecast documentado')

path = DATA_CLEAN / 'pipeline_cotizaciones.csv'
if not path.exists():
    st.warning('No existe pipeline_cotizaciones.csv. Ejecutar: python src/cotizaciones.py')
    st.stop()

df = pd.read_csv(path)
if df.empty:
    st.info('Sin registros en pipeline')
    st.stop()

df = apply_forecast_governance(df)
summary = forecast_summary(df)
mask = df['forecast_documentado']

c1, c2, c3, c4 = st.columns(4)
c1.metric('Registros comerciales', summary['registros'])
c2.metric(
    'Monto documentado',
    f"Gs {summary['monto_documentado']:,.0f}" if summary['forecast_documentados'] else 'N/D',
)
c3.metric(
    'Forecast ponderado documentado',
    f"Gs {summary['monto_ponderado_documentado']:,.0f}" if summary['forecast_documentados'] else 'N/D',
)
c4.metric('Pendientes de evidencia', summary['pendientes_evidencia'])

if summary['pendientes_evidencia']:
    st.warning(
        'Los registros sin monto y probabilidad documentados NO integran el forecast. '
        'Las sugerencias de recompra no son cotizaciones ni ventas esperadas.'
    )

st.divider()

estados = sorted(df['estado'].dropna().unique().tolist()) if 'estado' in df.columns else []
sel = st.multiselect('Estado', estados, default=estados)
view = df.copy()
if sel and 'estado' in view.columns:
    view = view[view['estado'].isin(sel)]

left, right = st.columns(2)
with left:
    estado = df.groupby('estado', dropna=False).size().reset_index(name='registros')
    st.plotly_chart(px.bar(estado, x='estado', y='registros'), use_container_width=True)
with right:
    origen = df.groupby('origen', dropna=False).size().reset_index(name='registros')
    st.plotly_chart(px.bar(origen, x='origen', y='registros'), use_container_width=True)

st.subheader('Pipeline y sugerencias')
st.dataframe(
    view.sort_values(
        ['forecast_documentado', 'monto_estimado_num'],
        ascending=[False, False],
        na_position='last',
    ),
    use_container_width=True,
)

st.subheader('Forecast documentado')
forecast = df[mask].copy()
if forecast.empty:
    st.info('No hay registros aptos para forecast ponderado con evidencia documentada.')
else:
    st.dataframe(
        forecast.sort_values('monto_ponderado_documentado', ascending=False),
        use_container_width=True,
    )
