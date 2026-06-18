"""
SIC-BA Dashboard Financiero v0.1
Dashboard simple en Streamlit para el Centro de Comando Financiero.

Ejecutar:
streamlit run src/dashboard_financiero.py
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / "data_clean"

st.set_page_config(page_title="SIC-BA Centro de Comando", layout="wide")

st.title("SIC-BA | Centro de Comando Financiero")
st.caption("Blanco & Asociados - Soluciones Integrales")


def load_csv(name: str) -> pd.DataFrame:
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


cobros = load_csv("fact_cobros.csv")
pagos = load_csv("fact_pagos.csv")
cheques = load_csv("fact_cheques.csv")
score = load_csv("score_clientes.csv")

col1, col2, col3, col4 = st.columns(4)

total_cobrar = pd.to_numeric(cobros.get("saldo", pd.Series(dtype=float)), errors="coerce").fillna(0).sum() if not cobros.empty else 0
total_pagar = pd.to_numeric(pagos.get("saldo", pd.Series(dtype=float)), errors="coerce").fillna(0).sum() if not pagos.empty else 0
total_cheques = pd.to_numeric(cheques.get("monto", pd.Series(dtype=float)), errors="coerce").fillna(0).sum() if not cheques.empty else 0
flujo_neto = total_cobrar - total_pagar - total_cheques

col1.metric("Cuentas por cobrar", f"Gs {total_cobrar:,.0f}")
col2.metric("Cuentas por pagar", f"Gs {total_pagar:,.0f}")
col3.metric("Cheques emitidos", f"Gs {total_cheques:,.0f}")
col4.metric("Flujo neto estimado", f"Gs {flujo_neto:,.0f}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Top clientes deudores")
    if not cobros.empty and "cliente" in cobros.columns:
        top = cobros.groupby("cliente", dropna=False)["saldo"].sum().sort_values(ascending=False).head(10).reset_index()
        st.dataframe(top, use_container_width=True)
        fig = px.bar(top, x="saldo", y="cliente", orientation="h", title="Top 10 clientes por saldo")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No existe fact_cobros.csv cargado.")

with right:
    st.subheader("Top proveedores por pagar")
    if not pagos.empty and "proveedor" in pagos.columns:
        top_p = pagos.groupby("proveedor", dropna=False)["saldo"].sum().sort_values(ascending=False).head(10).reset_index()
        st.dataframe(top_p, use_container_width=True)
        fig = px.bar(top_p, x="saldo", y="proveedor", orientation="h", title="Top 10 proveedores por saldo")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No existe fact_pagos.csv cargado.")

st.divider()

st.subheader("Score de clientes")
if not score.empty:
    st.dataframe(score.head(25), use_container_width=True)
else:
    st.info("Ejecutar primero: python src/score_clientes.py")
