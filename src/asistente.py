from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'

st.set_page_config(page_title='SIC-BA Asistente', layout='wide')
st.title('SIC-BA | Asistente Gerencial')


def load_csv(name):
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def fmt(v):
    return f'Gs {float(v):,.0f}'

cobros = load_csv('fact_cobros.csv')
pagos = load_csv('fact_pagos.csv')
cheques = load_csv('fact_cheques.csv')
ventas = load_csv('fact_ventas.csv')
score = load_csv('score_clientes.csv')
alertas = load_csv('alertas.csv')

opcion = st.selectbox('Consulta', ['Clientes por saldo', 'Proveedores por saldo', 'Cheques', 'Clientes por ventas', 'Clientes en riesgo', 'Alertas'])

if opcion == 'Clientes por saldo':
    if cobros.empty or 'cliente' not in cobros.columns:
        st.warning('No hay datos de cobros')
    else:
        cobros['saldo'] = pd.to_numeric(cobros.get('saldo', 0), errors='coerce').fillna(0)
        top = cobros.groupby('cliente')['saldo'].sum().sort_values(ascending=False).reset_index()
        st.metric('Total pendiente', fmt(top['saldo'].sum()))
        st.dataframe(top.head(30), use_container_width=True)

elif opcion == 'Proveedores por saldo':
    if pagos.empty or 'proveedor' not in pagos.columns:
        st.warning('No hay datos de pagos')
    else:
        pagos['saldo'] = pd.to_numeric(pagos.get('saldo', 0), errors='coerce').fillna(0)
        top = pagos.groupby('proveedor')['saldo'].sum().sort_values(ascending=False).reset_index()
        st.metric('Total pendiente', fmt(top['saldo'].sum()))
        st.dataframe(top.head(30), use_container_width=True)

elif opcion == 'Cheques':
    if cheques.empty:
        st.warning('No hay datos de cheques')
    else:
        st.dataframe(cheques.head(100), use_container_width=True)

elif opcion == 'Clientes por ventas':
    if ventas.empty or 'cliente' not in ventas.columns:
        st.warning('No hay datos de ventas')
    else:
        ventas['total_gs'] = pd.to_numeric(ventas.get('total_gs', 0), errors='coerce').fillna(0)
        top = ventas.groupby('cliente')['total_gs'].sum().sort_values(ascending=False).reset_index()
        st.metric('Ventas detectadas', fmt(top['total_gs'].sum()))
        st.dataframe(top.head(30), use_container_width=True)

elif opcion == 'Clientes en riesgo':
    if score.empty:
        st.warning('No hay score de clientes')
    else:
        st.dataframe(score.sort_values('score_cliente').head(30), use_container_width=True)

elif opcion == 'Alertas':
    if alertas.empty:
        st.warning('No hay alertas')
    else:
        st.dataframe(alertas, use_container_width=True)
