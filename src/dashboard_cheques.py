from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'

st.set_page_config(page_title='SIC-BA Cheques', layout='wide')
st.title('SIC-BA | Control de Cheques')
st.caption('Vencimientos, bancos, beneficiarios y alertas de cobertura')

path = DATA_CLEAN / 'fact_cheques.csv'
if not path.exists():
    st.warning('No existe fact_cheques.csv')
    st.stop()

cheques = pd.read_csv(path)
if cheques.empty:
    st.warning('No hay cheques cargados')
    st.stop()

fecha_col = 'vencimiento' if 'vencimiento' in cheques.columns else 'vence' if 'vence' in cheques.columns else None
if fecha_col is None or 'monto' not in cheques.columns:
    st.error('Faltan columnas vencimiento/vence o monto')
    st.stop()

cheques['fecha_vencimiento'] = pd.to_datetime(cheques[fecha_col], dayfirst=True, errors='coerce')
cheques['monto'] = pd.to_numeric(cheques['monto'], errors='coerce').fillna(0)
hoy = pd.Timestamp.today().normalize()
cheques['dias'] = (cheques['fecha_vencimiento'] - hoy).dt.days

c1, c2, c3, c4 = st.columns(4)
c1.metric('Total cheques', len(cheques))
c2.metric('Monto total', f"Gs {cheques['monto'].sum():,.0f}")
c3.metric('Vencen 7 dias', len(cheques[(cheques['dias'] >= 0) & (cheques['dias'] <= 7)]))
c4.metric('Monto 7 dias', f"Gs {cheques[(cheques['dias'] >= 0) & (cheques['dias'] <= 7)]['monto'].sum():,.0f}")

st.divider()

rango = st.selectbox('Rango', ['Todos', 'Vencidos', 'Proximos 7 dias', 'Proximos 15 dias', 'Proximos 30 dias'])
df = cheques.copy()
if rango == 'Vencidos':
    df = df[df['dias'] < 0]
elif rango == 'Proximos 7 dias':
    df = df[(df['dias'] >= 0) & (df['dias'] <= 7)]
elif rango == 'Proximos 15 dias':
    df = df[(df['dias'] >= 0) & (df['dias'] <= 15)]
elif rango == 'Proximos 30 dias':
    df = df[(df['dias'] >= 0) & (df['dias'] <= 30)]

st.subheader('Cheques')
st.dataframe(df.sort_values('fecha_vencimiento'), use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader('Por banco')
    if 'banco' in cheques.columns:
        banco = cheques.groupby('banco')['monto'].sum().sort_values(ascending=False).reset_index()
        st.plotly_chart(px.bar(banco, x='banco', y='monto'), use_container_width=True)
with right:
    st.subheader('Por beneficiario')
    if 'beneficiario' in cheques.columns:
        bene = cheques.groupby('beneficiario')['monto'].sum().sort_values(ascending=False).head(15).reset_index()
        st.plotly_chart(px.bar(bene, x='monto', y='beneficiario', orientation='h'), use_container_width=True)

st.subheader('Calendario mensual')
cheques['mes'] = cheques['fecha_vencimiento'].dt.to_period('M').astype(str)
mensual = cheques.groupby('mes')['monto'].sum().reset_index()
st.plotly_chart(px.line(mensual, x='mes', y='monto', markers=True), use_container_width=True)
