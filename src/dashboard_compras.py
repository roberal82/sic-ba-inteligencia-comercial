"""
SIC-BA Dashboard Compras y Proveedores v0.1

Ejecutar:
streamlit run src/dashboard_compras.py
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / "data_clean"

st.set_page_config(page_title="SIC-BA Compras", layout="wide")
st.title("SIC-BA | Dashboard Compras y Proveedores")
st.caption("Control de compras, proveedores, productos y cuentas por pagar")


def load_csv(name: str) -> pd.DataFrame:
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


compras = load_csv("fact_compras.csv")
pagos = load_csv("fact_pagos.csv")

if compras.empty and pagos.empty:
    st.warning("No existen datos de compras/proveedores. Ejecutar primero: python src/main.py")
    st.stop()

col1, col2, col3, col4 = st.columns(4)

total_compras = 0
cantidad_proveedores = 0
cantidad_productos = 0
total_pendiente = 0

if not compras.empty:
    compras["total"] = pd.to_numeric(compras.get("total", 0), errors="coerce").fillna(0)
    total_compras = compras["total"].sum()
    cantidad_proveedores = compras["proveedor"].nunique() if "proveedor" in compras.columns else 0
    cantidad_productos = compras["producto"].nunique() if "producto" in compras.columns else 0

if not pagos.empty:
    pagos["saldo"] = pd.to_numeric(pagos.get("saldo", 0), errors="coerce").fillna(0)
    total_pendiente = pagos["saldo"].sum()
    if cantidad_proveedores == 0 and "proveedor" in pagos.columns:
        cantidad_proveedores = pagos["proveedor"].nunique()

col1.metric("Compras Gs", f"{total_compras:,.0f}")
col2.metric("Proveedores", f"{cantidad_proveedores:,.0f}")
col3.metric("Productos comprados", f"{cantidad_productos:,.0f}")
col4.metric("Pendiente a pagar", f"Gs {total_pendiente:,.0f}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Top proveedores por compras")
    if not compras.empty and "proveedor" in compras.columns:
        top_proveedores = compras.groupby("proveedor", dropna=False)["total"].sum().sort_values(ascending=False).head(15).reset_index()
        st.dataframe(top_proveedores, use_container_width=True)
        fig = px.bar(top_proveedores, x="total", y="proveedor", orientation="h", title="Top proveedores por volumen de compra")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No existe fact_compras.csv con columna proveedor.")

with right:
    st.subheader("Top proveedores por saldo pendiente")
    if not pagos.empty and "proveedor" in pagos.columns:
        top_pagos = pagos.groupby("proveedor", dropna=False)["saldo"].sum().sort_values(ascending=False).head(15).reset_index()
        st.dataframe(top_pagos, use_container_width=True)
        fig = px.bar(top_pagos, x="saldo", y="proveedor", orientation="h", title="Top proveedores por deuda")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No existe fact_pagos.csv con columna proveedor.")

st.divider()

left2, right2 = st.columns(2)

with left2:
    st.subheader("Top productos comprados")
    if not compras.empty and "producto" in compras.columns:
        top_productos = compras.groupby("producto", dropna=False).agg(
            total=("total", "sum"),
            cantidad=("cantidad", "sum"),
        ).sort_values("total", ascending=False).head(20).reset_index()
        st.dataframe(top_productos, use_container_width=True)
        fig = px.bar(top_productos, x="total", y="producto", orientation="h", title="Top productos por compra")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No existe fact_compras.csv con columna producto.")

with right2:
    st.subheader("Compras por mes")
    if not compras.empty and "fecha" in compras.columns:
        compras["fecha_dt"] = pd.to_datetime(compras["fecha"], dayfirst=True, errors="coerce")
        compras["mes"] = compras["fecha_dt"].dt.to_period("M").astype(str)
        mensual = compras.groupby("mes", dropna=False)["total"].sum().reset_index()
        fig = px.line(mensual, x="mes", y="total", markers=True, title="Evolución mensual de compras")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay fechas de compras disponibles.")

st.divider()

st.subheader("Riesgo de concentración de proveedores")
if not compras.empty and "proveedor" in compras.columns and total_compras > 0:
    conc = compras.groupby("proveedor", dropna=False)["total"].sum().sort_values(ascending=False).reset_index()
    conc["participacion_%"] = (conc["total"] / total_compras * 100).round(2)
    conc["riesgo"] = conc["participacion_%"].apply(lambda x: "ALTO" if x >= 20 else "MEDIO" if x >= 10 else "BAJO")
    st.dataframe(conc.head(25), use_container_width=True)
else:
    st.info("No se pudo calcular concentración de proveedores.")
