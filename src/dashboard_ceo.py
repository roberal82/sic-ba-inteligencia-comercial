from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

from src.financial_governance import load_financial_gate

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'

st.set_page_config(page_title='SIC-BA CEO', layout='wide')
st.title('SIC-BA | CEO Dashboard')
st.caption('Pantalla unica de control ejecutivo con gates de calidad de datos')


def load_csv(name):
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def n(df, col):
    if df.empty or col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors='coerce').fillna(0)


def money_or_nd(value, enabled):
    return f'Gs {value:,.0f}' if enabled else 'N/D'


ventas = load_csv('fact_ventas.csv')
cobros = load_csv('fact_cobros.csv')
pagos = load_csv('fact_pagos.csv')
cheques = load_csv('fact_cheques.csv')
alertas = load_csv('alertas.csv')
score = load_csv('score_clientes.csv')
crm = load_csv('crm_clientes.csv')
financial_gate = load_financial_gate(DATA_CLEAN)

venta_total = n(ventas, 'total_gs').sum()
if financial_gate.official:
    pendiente_cobro = n(cobros, 'saldo').sum()
    pendiente_pago = n(pagos, 'saldo').sum()
    cheques_total = n(cheques, 'monto').sum()
else:
    pendiente_cobro = pendiente_pago = cheques_total = 0

# Regla de gobierno: NO calcular CxC - CxP - cheques. CxP y cheques pueden solaparse.
flujo_validado = None
alertas_rojas = len(alertas[alertas['nivel'] == 'ROJO']) if not alertas.empty and 'nivel' in alertas.columns else 0
score_prom = n(score, 'score_cliente').mean() if not score.empty else 0

if not financial_gate.official:
    st.error(
        'FINANZAS BLOQUEADAS — L4 NO-GO. CxC, CxP, cheques y caja se muestran como N/D. '
        f'Motivo: {financial_gate.reason}'
    )
else:
    st.success(f'Gate financiero L4 habilitado | corte: {financial_gate.cutoff}')

c1, c2, c3, c4 = st.columns(4)
c1.metric('Ventas detectadas', f'Gs {venta_total:,.0f}')
c2.metric('CxC oficial', money_or_nd(pendiente_cobro, financial_gate.official))
c3.metric('CxP oficial', money_or_nd(pendiente_pago, financial_gate.official))
c4.metric('Flujo neto validado', 'N/D')

c5, c6, c7, c8 = st.columns(4)
c5.metric('Cheques oficiales', money_or_nd(cheques_total, financial_gate.official))
c6.metric('Alertas rojas', alertas_rojas)
c7.metric('Score comercial promedio', f'{score_prom:.1f}')
c8.metric('Clientes CRM', len(crm) if not crm.empty else 0)

st.caption('Flujo neto permanece N/D hasta existir un MART de caja conciliado; no se compensa globalmente CxC/CxP/cheques.')
st.divider()

left, right = st.columns(2)
with left:
    st.subheader('Top clientes por ventas')
    if not ventas.empty and 'cliente' in ventas.columns:
        ventas = ventas.copy()
        ventas['total_gs'] = n(ventas, 'total_gs')
        top = ventas.groupby('cliente')['total_gs'].sum().sort_values(ascending=False).head(10).reset_index()
        st.dataframe(top, use_container_width=True)
        st.plotly_chart(px.bar(top, x='total_gs', y='cliente', orientation='h'), use_container_width=True)
with right:
    st.subheader('CxC por cliente')
    if financial_gate.official and not cobros.empty and 'cliente' in cobros.columns:
        cobros = cobros.copy()
        cobros['saldo'] = n(cobros, 'saldo')
        topd = cobros.groupby('cliente')['saldo'].sum().sort_values(ascending=False).head(10).reset_index()
        st.dataframe(topd, use_container_width=True)
        st.plotly_chart(px.bar(topd, x='saldo', y='cliente', orientation='h'), use_container_width=True)
    else:
        st.info('Bloqueado hasta L4 PASS con corte y evidencia documentados.')

st.divider()
left2, right2 = st.columns(2)
with left2:
    st.subheader('Margen real por cliente')
    st.info('N/D hasta completar ASIGNACION_COSTO documentada. No se publica margen inferido como rentabilidad real.')
with right2:
    st.subheader('Alertas principales')
    if not alertas.empty:
        show = alertas.sort_values('monto_referencia', ascending=False).head(10) if 'monto_referencia' in alertas.columns else alertas.head(10)
        st.dataframe(show, use_container_width=True)

st.divider()
st.subheader('Prioridades CRM')
if not crm.empty:
    sort_col = 'venta_total' if 'venta_total' in crm.columns else crm.columns[0]
    st.dataframe(crm.sort_values(sort_col, ascending=False).head(20), use_container_width=True)
else:
    st.info('Ejecutar: python src/crm.py')
