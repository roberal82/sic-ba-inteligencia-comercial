"""
SIC-BA Dashboard Comercial v0.1

Ejecutar:
streamlit run src/dashboard_comercial.py
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / "data_clean"

st.set_page_config(page_title="SIC-BA Comercial", layout="wide")
st.title("SIC-BA | Dashboard Comercial")
st.caption("Ventas, clientes, productos y ranking comercial")


def load_csv(name: str) -> pd.DataFrame:
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


ventas = load_csv("fact_ventas.csv")
ventas_producto = load_csv("fact_ventas_producto.csv")

if ventas.empty and ventas_producto.empty:
    st.warning("No existen datos comerciales. Ejecutar primero: python src/main.py")
    st.stop()

col1, col2, col3, col4 = st.columns(4)

venta_total = 0
facturas = 0
clientes = 0
productos = 0

if not ventas.empty:
    ventas["total_gs"] = pd.to_numeric(ventas.get("total_gs", 0), errors="coerce").fillna(0)
    venta_total = ventas["total_gs"].sum()
    facturas = ventas["factura"].nunique() if "factura" in ventas.columns else len(ventas)
    clientes = ventas["cliente"].nunique() if "cliente" in ventas.columns else 0

if not ventas_producto.empty:
    ventas_producto["total"] = pd.to_numeric(ventas_producto.get("total", 0), errors="coerce").fillna(0)
    productos = ventas_producto["producto"].nunique() if "producto" in ventas_producto.columns else 0
    if venta_total == 0:
        venta_total = ventas_producto["total"].sum()
    if clientes == 0 and "cliente" in ventas_producto.columns:
        clientes = ventas_producto["cliente"].nunique()

col1.metric("Ventas Gs", f"{venta_total:,.0f}")
col2.metric("Facturas", f"{facturas:,.0f}")
col3.metric("Clientes", f"{clientes:,.0f}")
col4.metric("Productos", f"{productos:,.0f}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Top clientes")
    if not ventas.empty and "cliente" in ventas.columns:
        top_clientes = ventas.groupby("cliente", dropna=False)["total_gs"].sum().sort_values(ascending=False).head(15).reset_index()
    elif not ventas_producto.empty and "cliente" in ventas_producto.columns:
        top_clientes = ventas_producto.groupby("cliente", dropna=False)["total"].sum().sort_values(ascending=False).head(15).reset_index()
        top_clientes = top_clientes.rename(columns={"total": "total_gs"})
    else:
        top_clientes = pd.DataFrame()

    if not top_clientes.empty:
        st.dataframe(top_clientes, use_container_width=True)
        fig = px.bar(top_clientes, x="total_gs", y="cliente", orientation="h", title="Top clientes por ventas")
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Top productos")
    if not ventas_producto.empty and "producto" in ventas_producto.columns:
        top_productos = ventas_producto.groupby("producto", dropna=False).agg(
            total=("total", "sum"),
            cantidad=("cantidad", "sum"),
        ).sort_values("total", ascending=False).head(15).reset_index()
        st.dataframe(top_productos, use_container_width=True)
        fig = px.bar(top_productos, x="total", y="producto", orientation="h", title="Top productos por ventas")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No existe fact_ventas_producto.csv.")

st.divider()

st.subheader("Ventas por mes")
if not ventas.empty and "fecha" in ventas.columns:
    ventas["fecha_dt"] = pd.to_datetime(ventas["fecha"], dayfirst=True, errors="coerce")
    ventas["mes"] = ventas["fecha_dt"].dt.to_period("M").astype(str)
    mensual = ventas.groupby("mes", dropna=False)["total_gs"].sum().reset_index()
    fig = px.line(mensual, x="mes", y="total_gs", markers=True, title="Evolución mensual de ventas")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No hay fechas de ventas disponibles.")
