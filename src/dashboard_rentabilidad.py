from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'

st.set_page_config(page_title='SIC-BA Rentabilidad', layout='wide')
st.title('SIC-BA | Rentabilidad Estimada')
st.caption('Utilidad estimada por cliente y producto')


def load_csv(name):
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)

cliente = load_csv('rentabilidad_cliente.csv')
producto = load_csv('rentabilidad_producto.csv')
detalle = load_csv('rentabilidad_detalle.csv')

if cliente.empty and producto.empty:
    st.warning('No existe rentabilidad. Ejecutar primero: python src/rentabilidad.py')
    st.stop()

if not cliente.empty:
    venta = pd.to_numeric(cliente.get('venta', 0), errors='coerce').fillna(0).sum()
    utilidad = pd.to_numeric(cliente.get('utilidad_estimada', 0), errors='coerce').fillna(0).sum()
    margen = utilidad / venta * 100 if venta else 0
else:
    venta = utilidad = margen = 0

c1, c2, c3 = st.columns(3)
c1.metric('Venta', f'Gs {venta:,.0f}')
c2.metric('Utilidad estimada', f'Gs {utilidad:,.0f}')
c3.metric('Margen estimado', f'{margen:.1f}%')

st.divider()

left, right = st.columns(2)
with left:
    st.subheader('Rentabilidad por cliente')
    if not cliente.empty:
        st.dataframe(cliente, use_container_width=True)
        fig = px.bar(cliente.head(15), x='utilidad_estimada', y='cliente', orientation='h', title='Top clientes por utilidad')
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader('Rentabilidad por producto')
    if not producto.empty:
        st.dataframe(producto, use_container_width=True)
        fig = px.bar(producto.head(15), x='utilidad_estimada', y='producto', orientation='h', title='Top productos por utilidad')
        st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader('Detalle')
if not detalle.empty:
    st.dataframe(detalle.head(200), use_container_width=True)
