from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'

st.set_page_config(page_title='SIC-BA ABC', layout='wide')
st.title('SIC-BA | ABC Comercial')
st.caption('Clasificacion ABC de clientes, productos y proveedores')


def load_csv(name):
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)

opcion = st.selectbox('Vista', ['Clientes', 'Productos', 'Proveedores'])
file_map = {
    'Clientes': ('abc_clientes.csv', 'cliente', 'total_gs'),
    'Productos': ('abc_productos.csv', 'producto', 'total'),
    'Proveedores': ('abc_proveedores.csv', 'proveedor', 'total'),
}

file_name, label_col, value_col = file_map[opcion]
df = load_csv(file_name)

if df.empty:
    st.warning('No existe archivo ABC. Ejecutar: python src/abc.py')
    st.stop()

st.dataframe(df, use_container_width=True)

left, right = st.columns(2)
with left:
    resumen = df.groupby('clase_abc').agg(items=(label_col, 'count'), valor=(value_col, 'sum')).reset_index()
    st.plotly_chart(px.bar(resumen, x='clase_abc', y='valor', title='Valor por clase ABC'), use_container_width=True)
with right:
    st.plotly_chart(px.pie(resumen, names='clase_abc', values='items', title='Cantidad por clase ABC'), use_container_width=True)

st.subheader('Top ranking')
st.plotly_chart(px.bar(df.head(20), x=value_col, y=label_col, orientation='h'), use_container_width=True)
