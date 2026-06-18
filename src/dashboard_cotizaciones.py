from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'

st.set_page_config(page_title='SIC-BA Cotizaciones', layout='wide')
st.title('SIC-BA | Pipeline de Cotizaciones')
st.caption('Solicitud, seguimiento, negociacion, orden de compra y facturacion')

path = DATA_CLEAN / 'pipeline_cotizaciones.csv'
if not path.exists():
    st.warning('No existe pipeline_cotizaciones.csv. Ejecutar: python src/cotizaciones.py')
    st.stop()

df = pd.read_csv(path)
if df.empty:
    st.info('Sin cotizaciones en pipeline')
    st.stop()

df['monto_estimado'] = pd.to_numeric(df.get('monto_estimado', 0), errors='coerce').fillna(0)
df['probabilidad_pct'] = pd.to_numeric(df.get('probabilidad_pct', 0), errors='coerce').fillna(0)
df['monto_ponderado'] = df['monto_estimado'] * df['probabilidad_pct'] / 100

c1, c2, c3, c4 = st.columns(4)
c1.metric('Cotizaciones', len(df))
c2.metric('Monto estimado', f"Gs {df['monto_estimado'].sum():,.0f}")
c3.metric('Monto ponderado', f"Gs {df['monto_ponderado'].sum():,.0f}")
c4.metric('Clientes', df['cliente'].nunique() if 'cliente' in df.columns else 0)

st.divider()

estados = sorted(df['estado'].dropna().unique().tolist()) if 'estado' in df.columns else []
sel = st.multiselect('Estado', estados, default=estados)
view = df.copy()
if sel and 'estado' in view.columns:
    view = view[view['estado'].isin(sel)]

left, right = st.columns(2)
with left:
    estado = df.groupby('estado')['monto_estimado'].sum().reset_index()
    st.plotly_chart(px.bar(estado, x='estado', y='monto_estimado'), use_container_width=True)
with right:
    origen = df.groupby('origen')['monto_estimado'].sum().reset_index()
    st.plotly_chart(px.bar(origen, x='origen', y='monto_estimado'), use_container_width=True)

st.subheader('Pipeline')
st.dataframe(view.sort_values('monto_estimado', ascending=False), use_container_width=True)

st.subheader('Top oportunidades a cotizar')
st.dataframe(df.sort_values('monto_ponderado', ascending=False).head(20), use_container_width=True)
