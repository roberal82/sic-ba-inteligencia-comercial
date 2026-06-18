from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'

st.set_page_config(page_title='SIC-BA Oportunidades', layout='wide')
st.title('SIC-BA | Centro de Oportunidades')
st.caption('Recuperacion de clientes y venta cruzada')

path = DATA_CLEAN / 'oportunidades.csv'
if not path.exists():
    st.warning('No existe oportunidades.csv. Ejecutar: python src/oportunidades.py')
    st.stop()

df = pd.read_csv(path)
if df.empty:
    st.info('No se detectaron oportunidades')
    st.stop()

df['monto_referencia'] = pd.to_numeric(df.get('monto_referencia', 0), errors='coerce').fillna(0)

c1, c2, c3 = st.columns(3)
c1.metric('Oportunidades', len(df))
c2.metric('Monto referencia', f"Gs {df['monto_referencia'].sum():,.0f}")
c3.metric('Clientes', df['cliente'].nunique() if 'cliente' in df.columns else 0)

st.divider()

left, right = st.columns(2)
with left:
    if 'tipo_oportunidad' in df.columns:
        tipo = df.groupby('tipo_oportunidad').size().reset_index(name='cantidad')
        st.plotly_chart(px.bar(tipo, x='tipo_oportunidad', y='cantidad'), use_container_width=True)
with right:
    if 'prioridad' in df.columns:
        pr = df.groupby('prioridad')['monto_referencia'].sum().reset_index()
        st.plotly_chart(px.bar(pr, x='prioridad', y='monto_referencia'), use_container_width=True)

st.subheader('Listado')
st.dataframe(df.sort_values('monto_referencia', ascending=False), use_container_width=True)

st.subheader('Acciones sugeridas')
for _, r in df.sort_values('monto_referencia', ascending=False).head(15).iterrows():
    st.markdown(f"### {r.get('cliente', '')} | {r.get('tipo_oportunidad', '')}")
    st.write(r.get('detalle', ''))
    st.info(r.get('accion', ''))
