from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'

st.set_page_config(page_title='SIC-BA Forecast', layout='wide')
st.title('SIC-BA | Forecast')
st.caption('Proyeccion simple de ventas, cobros y pagos')


def load_csv(name):
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)

ventas = load_csv('forecast_ventas.csv')
cobros = load_csv('forecast_cobros.csv')
pagos = load_csv('forecast_pagos.csv')

st.info('Ejecutar antes: python src/forecast.py')

for titulo, df, col in [
    ('Forecast ventas', ventas, 'total_gs'),
    ('Forecast cobros', cobros, 'saldo'),
    ('Forecast pagos', pagos, 'saldo'),
]:
    st.subheader(titulo)
    if df.empty:
        st.warning('Sin datos')
        continue
    df['mes'] = pd.to_datetime(df['mes'], errors='coerce')
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    st.dataframe(df, use_container_width=True)
    fig = px.line(df, x='mes', y=col, color='tipo', markers=True, title=titulo)
    st.plotly_chart(fig, use_container_width=True)
