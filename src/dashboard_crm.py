from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'

st.set_page_config(page_title='SIC-BA CRM', layout='wide')
st.title('SIC-BA | CRM Comercial')
st.caption('Cartera de clientes, prioridad y próximas acciones')

path = DATA_CLEAN / 'crm_clientes.csv'
if not path.exists():
    st.warning('No existe crm_clientes.csv. Ejecutar: python src/crm.py')
    st.stop()

crm = pd.read_csv(path)
for col in ['venta_total', 'saldo_pendiente', 'score']:
    if col in crm.columns:
        crm[col] = pd.to_numeric(crm[col], errors='coerce').fillna(0)

c1, c2, c3, c4 = st.columns(4)
c1.metric('Clientes', len(crm))
c2.metric('Ventas cartera', f"Gs {crm.get('venta_total', pd.Series(dtype=float)).sum():,.0f}")
c3.metric('Saldo pendiente', f"Gs {crm.get('saldo_pendiente', pd.Series(dtype=float)).sum():,.0f}")
c4.metric('Score promedio', f"{crm.get('score', pd.Series(dtype=float)).mean():.1f}")

st.divider()

prioridades = sorted(crm['prioridad'].dropna().unique().tolist()) if 'prioridad' in crm.columns else []
sel = st.multiselect('Prioridad', prioridades, default=prioridades)
df = crm.copy()
if sel and 'prioridad' in df.columns:
    df = df[df['prioridad'].isin(sel)]

left, right = st.columns(2)
with left:
    st.subheader('Clientes por prioridad')
    if 'prioridad' in crm.columns:
        resumen = crm.groupby('prioridad').size().reset_index(name='clientes')
        st.plotly_chart(px.bar(resumen, x='prioridad', y='clientes'), use_container_width=True)
with right:
    st.subheader('Próximas acciones')
    if 'proxima_accion' in crm.columns:
        acciones = crm.groupby('proxima_accion').size().reset_index(name='clientes')
        st.plotly_chart(px.bar(acciones, x='proxima_accion', y='clientes'), use_container_width=True)

st.subheader('Cartera CRM')
st.dataframe(df.sort_values(['prioridad', 'saldo_pendiente'], ascending=[True, False]), use_container_width=True)

st.subheader('Clientes prioritarios')
st.dataframe(df.sort_values('saldo_pendiente', ascending=False).head(20), use_container_width=True)
