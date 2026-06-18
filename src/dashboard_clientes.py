"""
SIC-BA Dashboard Inteligencia de Clientes v0.1

Objetivo:
- Vista Cliente 360.
- Score de clientes.
- Ranking de clientes por venta, deuda y frecuencia.

Ejecutar:
python src/score_clientes.py
streamlit run src/dashboard_clientes.py
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / "data_clean"

st.set_page_config(page_title="SIC-BA Clientes", layout="wide")
st.title("SIC-BA | Inteligencia de Clientes")
st.caption("Cliente 360, score, deuda, ventas y riesgo comercial")


def load_csv(name: str) -> pd.DataFrame:
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


ventas = load_csv("fact_ventas.csv")
cobros = load_csv("fact_cobros.csv")
score = load_csv("score_clientes.csv")
ventas_producto = load_csv("fact_ventas_producto.csv")

if ventas.empty and cobros.empty and score.empty:
    st.warning("No existen datos de clientes. Ejecutar: python src/main.py y python src/score_clientes.py")
    st.stop()

# Normalización básica
if not ventas.empty:
    ventas["total_gs"] = num(ventas.get("total_gs", 0))
if not cobros.empty:
    cobros["saldo"] = num(cobros.get("saldo", 0))
if not ventas_producto.empty:
    ventas_producto["total"] = num(ventas_producto.get("total", 0))

clientes_set = set()
for df in [ventas, cobros, score, ventas_producto]:
    if not df.empty and "cliente" in df.columns:
        clientes_set.update(df["cliente"].dropna().astype(str).unique().tolist())

clientes = sorted(clientes_set)
cliente_sel = st.sidebar.selectbox("Seleccionar cliente", clientes) if clientes else None

# KPIs generales
ventas_total = ventas["total_gs"].sum() if not ventas.empty and "total_gs" in ventas.columns else 0
saldo_total = cobros["saldo"].sum() if not cobros.empty and "saldo" in cobros.columns else 0
clientes_count = len(clientes)
score_promedio = num(score.get("score_cliente", pd.Series(dtype=float))).mean() if not score.empty and "score_cliente" in score.columns else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Clientes detectados", f"{clientes_count:,.0f}")
col2.metric("Ventas totales", f"Gs {ventas_total:,.0f}")
col3.metric("Saldo pendiente", f"Gs {saldo_total:,.0f}")
col4.metric("Score promedio", f"{score_promedio:,.1f}")

st.divider()

st.subheader("Ranking de clientes")
left, right = st.columns(2)

with left:
    st.markdown("### Top clientes por ventas")
    if not ventas.empty and "cliente" in ventas.columns:
        top_v = ventas.groupby("cliente", dropna=False)["total_gs"].sum().sort_values(ascending=False).head(15).reset_index()
        st.dataframe(top_v, use_container_width=True)
        st.plotly_chart(px.bar(top_v, x="total_gs", y="cliente", orientation="h"), use_container_width=True)
    elif not ventas_producto.empty and "cliente" in ventas_producto.columns:
        top_vp = ventas_producto.groupby("cliente", dropna=False)["total"].sum().sort_values(ascending=False).head(15).reset_index()
        st.dataframe(top_vp, use_container_width=True)
        st.plotly_chart(px.bar(top_vp, x="total", y="cliente", orientation="h"), use_container_width=True)
    else:
        st.info("No hay ventas por cliente.")

with right:
    st.markdown("### Top clientes por deuda")
    if not cobros.empty and "cliente" in cobros.columns:
        top_d = cobros.groupby("cliente", dropna=False)["saldo"].sum().sort_values(ascending=False).head(15).reset_index()
        st.dataframe(top_d, use_container_width=True)
        st.plotly_chart(px.bar(top_d, x="saldo", y="cliente", orientation="h"), use_container_width=True)
    else:
        st.info("No hay pendientes por cobrar.")

st.divider()

st.subheader("Score de clientes")
if not score.empty:
    st.dataframe(score.sort_values("score_cliente", ascending=False), use_container_width=True)
    if "semaforo" in score.columns:
        resumen_score = score.groupby("semaforo", dropna=False).size().reset_index(name="clientes")
        st.plotly_chart(px.pie(resumen_score, names="semaforo", values="clientes", title="Distribución por semáforo"), use_container_width=True)
else:
    st.info("No existe score_clientes.csv. Ejecutar: python src/score_clientes.py")

st.divider()

if cliente_sel:
    st.subheader(f"Cliente 360 | {cliente_sel}")

    ventas_c = ventas[ventas["cliente"].astype(str) == cliente_sel] if not ventas.empty and "cliente" in ventas.columns else pd.DataFrame()
    cobros_c = cobros[cobros["cliente"].astype(str) == cliente_sel] if not cobros.empty and "cliente" in cobros.columns else pd.DataFrame()
    score_c = score[score["cliente"].astype(str) == cliente_sel] if not score.empty and "cliente" in score.columns else pd.DataFrame()
    vp_c = ventas_producto[ventas_producto["cliente"].astype(str) == cliente_sel] if not ventas_producto.empty and "cliente" in ventas_producto.columns else pd.DataFrame()

    venta_cliente = ventas_c["total_gs"].sum() if not ventas_c.empty and "total_gs" in ventas_c.columns else (vp_c["total"].sum() if not vp_c.empty and "total" in vp_c.columns else 0)
    deuda_cliente = cobros_c["saldo"].sum() if not cobros_c.empty and "saldo" in cobros_c.columns else 0
    facturas_cliente = ventas_c["factura"].nunique() if not ventas_c.empty and "factura" in ventas_c.columns else 0
    score_cliente = float(score_c["score_cliente"].iloc[0]) if not score_c.empty and "score_cliente" in score_c.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ventas", f"Gs {venta_cliente:,.0f}")
    c2.metric("Saldo pendiente", f"Gs {deuda_cliente:,.0f}")
    c3.metric("Facturas", f"{facturas_cliente:,.0f}")
    c4.metric("Score", f"{score_cliente:,.1f}")

    l1, l2 = st.columns(2)
    with l1:
        st.markdown("### Facturas / ventas")
        if not ventas_c.empty:
            st.dataframe(ventas_c, use_container_width=True)
        else:
            st.info("Sin ventas resumidas para este cliente.")
    with l2:
        st.markdown("### Pendientes por cobrar")
        if not cobros_c.empty:
            st.dataframe(cobros_c, use_container_width=True)
        else:
            st.info("Sin deuda pendiente detectada.")

    st.markdown("### Productos comprados")
    if not vp_c.empty and "producto" in vp_c.columns:
        prod = vp_c.groupby("producto", dropna=False).agg(total=("total", "sum"), cantidad=("cantidad", "sum")).sort_values("total", ascending=False).head(20).reset_index()
        st.dataframe(prod, use_container_width=True)
        st.plotly_chart(px.bar(prod, x="total", y="producto", orientation="h"), use_container_width=True)
    else:
        st.info("Sin detalle de productos para este cliente.")
