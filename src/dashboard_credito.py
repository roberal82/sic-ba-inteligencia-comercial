from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'

st.set_page_config(page_title='SIC-BA Credito', layout='wide')
st.title('SIC-BA | Control de Lineas de Credito')
st.caption('Uso de linea, disponible y semaforo de credito')

path = DATA_CLEAN / 'lineas_credito.csv'
if not path.exists():
    st.warning('No existe lineas_credito.csv. Ejecutar: python src/lineas_credito.py')
    st.stop()

df = pd.read_csv(path)
if df.empty:
    st.info('Sin datos de credito')
    st.stop()

for col in ['linea_credito', 'saldo_utilizado', 'disponible', 'uso_pct']:
    df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)

c1, c2, c3, c4 = st.columns(4)
c1.metric('Clientes', len(df))
c2.metric('Linea total', f"Gs {df['linea_credito'].sum():,.0f}")
c3.metric('Utilizado', f"Gs {df['saldo_utilizado'].sum():,.0f}")
c4.metric('Disponible', f"Gs {df['disponible'].sum():,.0f}")

st.divider()

estados = sorted(df['estado_credito'].dropna().unique().tolist()) if 'estado_credito' in df.columns else []
sel = st.multiselect('Estado', estados, default=estados)
view = df.copy()
if sel and 'estado_credito' in view.columns:
    view = view[view['estado_credito'].isin(sel)]

left, right = st.columns(2)
with left:
    resumen = df.groupby('estado_credito').agg(clientes=('cliente', 'count'), saldo=('saldo_utilizado', 'sum')).reset_index()
    st.plotly_chart(px.bar(resumen, x='estado_credito', y='saldo', title='Saldo por estado'), use_container_width=True)
with right:
    top = df.sort_values('uso_pct', ascending=False).head(20)
    st.plotly_chart(px.bar(top, x='uso_pct', y='cliente', orientation='h', title='Uso de linea %'), use_container_width=True)

st.subheader('Lineas de credito')
st.dataframe(view.sort_values('uso_pct', ascending=False), use_container_width=True)

st.subheader('Acciones criticas')
st.dataframe(df[df['estado_credito'].isin(['ROJO', 'AMARILLO'])].sort_values('uso_pct', ascending=False), use_container_width=True)
