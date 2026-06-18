from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'

st.set_page_config(page_title='SIC-BA CEO', layout='wide')
st.title('SIC-BA | CEO Dashboard')
st.caption('Pantalla unica de control ejecutivo')


def load_csv(name):
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def n(df, col):
    if df.empty or col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors='coerce').fillna(0)

ventas = load_csv('fact_ventas.csv')
cobros = load_csv('fact_cobros.csv')
pagos = load_csv('fact_pagos.csv')
cheques = load_csv('fact_cheques.csv')
alertas = load_csv('alertas.csv')
score = load_csv('score_clientes.csv')
rent_cliente = load_csv('rentabilidad_cliente.csv')
crm = load_csv('crm_clientes.csv')

venta_total = n(ventas, 'total_gs').sum()
pendiente_cobro = n(cobros, 'saldo').sum()
pendiente_pago = n(pagos, 'saldo').sum()
cheques_total = n(cheques, 'monto').sum()
flujo_estimado = pendiente_cobro - pendiente_pago - cheques_total
alertas_rojas = len(alertas[alertas['nivel'] == 'ROJO']) if not alertas.empty and 'nivel' in alertas.columns else 0
score_prom = n(score, 'score_cliente').mean() if not score.empty else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric('Ventas detectadas', f'Gs {venta_total:,.0f}')
c2.metric('Pendiente cobrar', f'Gs {pendiente_cobro:,.0f}')
c3.metric('Pendiente pagar', f'Gs {pendiente_pago:,.0f}')
c4.metric('Flujo estimado', f'Gs {flujo_estimado:,.0f}')

c5, c6, c7, c8 = st.columns(4)
c5.metric('Cheques', f'Gs {cheques_total:,.0f}')
c6.metric('Alertas rojas', alertas_rojas)
c7.metric('Score promedio', f'{score_prom:.1f}')
c8.metric('Clientes CRM', len(crm) if not crm.empty else 0)

st.divider()

left, right = st.columns(2)
with left:
    st.subheader('Top clientes por ventas')
    if not ventas.empty and 'cliente' in ventas.columns:
        ventas['total_gs'] = n(ventas, 'total_gs')
        top = ventas.groupby('cliente')['total_gs'].sum().sort_values(ascending=False).head(10).reset_index()
        st.dataframe(top, use_container_width=True)
        st.plotly_chart(px.bar(top, x='total_gs', y='cliente', orientation='h'), use_container_width=True)
with right:
    st.subheader('Top clientes por deuda')
    if not cobros.empty and 'cliente' in cobros.columns:
        cobros['saldo'] = n(cobros, 'saldo')
        topd = cobros.groupby('cliente')['saldo'].sum().sort_values(ascending=False).head(10).reset_index()
        st.dataframe(topd, use_container_width=True)
        st.plotly_chart(px.bar(topd, x='saldo', y='cliente', orientation='h'), use_container_width=True)

st.divider()

left2, right2 = st.columns(2)
with left2:
    st.subheader('Rentabilidad por cliente')
    if not rent_cliente.empty:
        st.dataframe(rent_cliente.head(15), use_container_width=True)
with right2:
    st.subheader('Alertas principales')
    if not alertas.empty:
        show = alertas.sort_values('monto_referencia', ascending=False).head(10) if 'monto_referencia' in alertas.columns else alertas.head(10)
        st.dataframe(show, use_container_width=True)

st.divider()
st.subheader('Prioridades CRM')
if not crm.empty:
    st.dataframe(crm.sort_values('saldo_pendiente', ascending=False).head(20), use_container_width=True)
else:
    st.info('Ejecutar: python src/crm.py')
