"""
SIC-BA Dashboard Tesorería y Flujo de Caja v0.1

Objetivo:
- Proyectar flujo de caja 7/30/60/90 días.
- Cruzar cobros pendientes, pagos pendientes y cheques emitidos.

Ejecutar:
streamlit run src/dashboard_tesoreria.py
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / "data_clean"

st.set_page_config(page_title="SIC-BA Tesorería", layout="wide")
st.title("SIC-BA | Dashboard Tesorería y Flujo de Caja")
st.caption("Proyección de caja 7, 30, 60 y 90 días")


def load_csv(name: str) -> pd.DataFrame:
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def to_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, dayfirst=True, errors="coerce")


def to_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


cobros = load_csv("fact_cobros.csv")
pagos = load_csv("fact_pagos.csv")
cheques = load_csv("fact_cheques.csv")

if cobros.empty and pagos.empty and cheques.empty:
    st.warning("No existen datos de tesorería. Ejecutar primero: python src/main.py")
    st.stop()

hoy = pd.Timestamp.today().normalize()
st.sidebar.header("Parámetros")
saldo_inicial = st.sidebar.number_input("Saldo bancario inicial Gs", min_value=-10_000_000_000, max_value=10_000_000_000, value=0, step=1_000_000)

movimientos = []

if not cobros.empty and "vencimiento" in cobros.columns:
    cobros["fecha"] = to_date(cobros["vencimiento"])
    cobros["monto"] = to_number(cobros.get("saldo", 0))
    cobros_tmp = cobros[["fecha", "monto"]].copy()
    cobros_tmp["tipo"] = "Cobro esperado"
    cobros_tmp["signo"] = 1
    cobros_tmp["detalle"] = cobros.get("cliente", "Cliente")
    movimientos.append(cobros_tmp)

if not pagos.empty and "vencimiento" in pagos.columns:
    pagos["fecha"] = to_date(pagos["vencimiento"])
    pagos["monto"] = to_number(pagos.get("saldo", 0))
    pagos_tmp = pagos[["fecha", "monto"]].copy()
    pagos_tmp["tipo"] = "Pago proveedor"
    pagos_tmp["signo"] = -1
    pagos_tmp["detalle"] = pagos.get("proveedor", "Proveedor")
    movimientos.append(pagos_tmp)

if not cheques.empty:
    fecha_col = "vencimiento" if "vencimiento" in cheques.columns else "vence" if "vence" in cheques.columns else None
    monto_col = "monto" if "monto" in cheques.columns else None
    if fecha_col and monto_col:
        cheques["fecha"] = to_date(cheques[fecha_col])
        cheques["monto"] = to_number(cheques[monto_col])
        cheques_tmp = cheques[["fecha", "monto"]].copy()
        cheques_tmp["tipo"] = "Cheque emitido"
        cheques_tmp["signo"] = -1
        cheques_tmp["detalle"] = cheques.get("beneficiario", "Cheque")
        movimientos.append(cheques_tmp)

if not movimientos:
    st.error("No se pudieron construir movimientos de caja. Revisar columnas de fecha/monto.")
    st.stop()

flujo = pd.concat(movimientos, ignore_index=True)
flujo = flujo.dropna(subset=["fecha"])
flujo["impacto"] = flujo["monto"] * flujo["signo"]
flujo["dias"] = (flujo["fecha"] - hoy).dt.days
flujo = flujo[flujo["dias"] >= 0]


def sum_window(days: int, tipo: str | None = None) -> float:
    df = flujo[(flujo["dias"] >= 0) & (flujo["dias"] <= days)]
    if tipo:
        df = df[df["tipo"] == tipo]
    return float(df["monto"].sum())


cobros_7 = sum_window(7, "Cobro esperado")
pagos_7 = sum_window(7, "Pago proveedor")
cheques_7 = sum_window(7, "Cheque emitido")
flujo_7 = saldo_inicial + cobros_7 - pagos_7 - cheques_7

cobros_30 = sum_window(30, "Cobro esperado")
pagos_30 = sum_window(30, "Pago proveedor")
cheques_30 = sum_window(30, "Cheque emitido")
flujo_30 = saldo_inicial + cobros_30 - pagos_30 - cheques_30

cobros_60 = sum_window(60, "Cobro esperado")
pagos_60 = sum_window(60, "Pago proveedor")
cheques_60 = sum_window(60, "Cheque emitido")
flujo_60 = saldo_inicial + cobros_60 - pagos_60 - cheques_60

cobros_90 = sum_window(90, "Cobro esperado")
pagos_90 = sum_window(90, "Pago proveedor")
cheques_90 = sum_window(90, "Cheque emitido")
flujo_90 = saldo_inicial + cobros_90 - pagos_90 - cheques_90

ratio_30 = cobros_30 / (pagos_30 + cheques_30) if (pagos_30 + cheques_30) > 0 else 999
semaforo = "VERDE" if ratio_30 > 1.20 else "AMARILLO" if ratio_30 >= 1.00 else "ROJO"

col1, col2, col3, col4 = st.columns(4)
col1.metric("Flujo 7 días", f"Gs {flujo_7:,.0f}")
col2.metric("Flujo 30 días", f"Gs {flujo_30:,.0f}")
col3.metric("Flujo 60 días", f"Gs {flujo_60:,.0f}")
col4.metric("Flujo 90 días", f"Gs {flujo_90:,.0f}")

col5, col6, col7 = st.columns(3)
col5.metric("Cobros 30 días", f"Gs {cobros_30:,.0f}")
col6.metric("Salidas 30 días", f"Gs {(pagos_30 + cheques_30):,.0f}")
col7.metric("Liquidez operativa", f"{ratio_30:.2f} | {semaforo}")

st.divider()

st.subheader("Proyección diaria de caja")
if not flujo.empty:
    diario = flujo.groupby("fecha", dropna=False)["impacto"].sum().reset_index().sort_values("fecha")
    diario["saldo_proyectado"] = saldo_inicial + diario["impacto"].cumsum()
    fig = px.line(diario, x="fecha", y="saldo_proyectado", markers=True, title="Saldo proyectado acumulado")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(diario, use_container_width=True)

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Entradas próximas 30 días")
    entradas = flujo[(flujo["tipo"] == "Cobro esperado") & (flujo["dias"] <= 30)].sort_values("fecha")
    st.dataframe(entradas[["fecha", "detalle", "monto", "dias"]].head(50), use_container_width=True)

with right:
    st.subheader("Salidas próximas 30 días")
    salidas = flujo[(flujo["tipo"].isin(["Pago proveedor", "Cheque emitido"])) & (flujo["dias"] <= 30)].sort_values("fecha")
    st.dataframe(salidas[["fecha", "tipo", "detalle", "monto", "dias"]].head(50), use_container_width=True)

st.divider()

st.subheader("Resumen por tipo de movimiento")
resumen = flujo.groupby("tipo", dropna=False).agg(
    monto_total=("monto", "sum"),
    registros=("monto", "count"),
).reset_index()
st.dataframe(resumen, use_container_width=True)
fig = px.bar(resumen, x="tipo", y="monto_total", title="Monto total por tipo de movimiento")
st.plotly_chart(fig, use_container_width=True)
