from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'

st.set_page_config(page_title='SIC-BA Alertas', layout='wide')
st.title('SIC-BA | Centro de Alertas')
st.caption('Cobranza, tesoreria, proveedores, clientes y riesgo comercial')

alertas_path = DATA_CLEAN / 'alertas.csv'
reporte_path = DATA_CLEAN / 'reporte_ejecutivo_diario.md'

if not alertas_path.exists():
    st.warning('No existe alertas.csv. Ejecutar primero: python src/alertas.py')
    st.stop()

alertas = pd.read_csv(alertas_path)

if alertas.empty:
    st.success('No hay alertas activas.')
    st.stop()

col1, col2, col3, col4 = st.columns(4)
total = len(alertas)
rojas = len(alertas[alertas['nivel'] == 'ROJO']) if 'nivel' in alertas.columns else 0
amarillas = len(alertas[alertas['nivel'] == 'AMARILLO']) if 'nivel' in alertas.columns else 0
monto_total = pd.to_numeric(alertas.get('monto_referencia', 0), errors='coerce').fillna(0).sum()

col1.metric('Alertas', total)
col2.metric('Rojas', rojas)
col3.metric('Amarillas', amarillas)
col4.metric('Monto referencia', f'Gs {monto_total:,.0f}')

st.divider()

f1, f2 = st.columns(2)
with f1:
    niveles = sorted(alertas['nivel'].dropna().unique().tolist()) if 'nivel' in alertas.columns else []
    nivel_sel = st.multiselect('Nivel', niveles, default=niveles)
with f2:
    modulos = sorted(alertas['modulo'].dropna().unique().tolist()) if 'modulo' in alertas.columns else []
    modulo_sel = st.multiselect('Modulo', modulos, default=modulos)

df = alertas.copy()
if nivel_sel and 'nivel' in df.columns:
    df = df[df['nivel'].isin(nivel_sel)]
if modulo_sel and 'modulo' in df.columns:
    df = df[df['modulo'].isin(modulo_sel)]

left, right = st.columns(2)
with left:
    if 'nivel' in alertas.columns:
        resumen_nivel = alertas.groupby('nivel', dropna=False).size().reset_index(name='cantidad')
        st.plotly_chart(px.bar(resumen_nivel, x='nivel', y='cantidad', title='Alertas por nivel'), use_container_width=True)
with right:
    if 'modulo' in alertas.columns:
        resumen_mod = alertas.groupby('modulo', dropna=False).size().reset_index(name='cantidad')
        st.plotly_chart(px.bar(resumen_mod, x='modulo', y='cantidad', title='Alertas por modulo'), use_container_width=True)

st.subheader('Listado de alertas')
if 'monto_referencia' in df.columns:
    df = df.sort_values('monto_referencia', ascending=False)
st.dataframe(df, use_container_width=True)

st.subheader('Acciones recomendadas')
for _, r in df.head(10).iterrows():
    st.markdown(f"### {r.get('nivel', '')} | {r.get('titulo', '')}")
    st.write(r.get('detalle', ''))
    st.info(r.get('accion_recomendada', ''))

st.divider()
st.subheader('Reporte Ejecutivo Diario')
if reporte_path.exists():
    st.markdown(reporte_path.read_text(encoding='utf-8'))
else:
    st.info('No existe reporte_ejecutivo_diario.md.')
