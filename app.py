"""
SIC-BA App Principal v0.1

Aplicacion unificada para navegar los modulos del Sistema de Inteligencia Comercial.

Ejecutar:
streamlit run app.py
"""

from pathlib import Path
import subprocess
import sys
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA_CLEAN = ROOT / "data_clean"

st.set_page_config(page_title="SIC-BA", layout="wide")

st.title("SIC-BA | Sistema de Inteligencia Comercial")
st.caption("Blanco & Asociados - Centro de comando gerencial")

st.sidebar.title("Navegacion")
modulo = st.sidebar.radio(
    "Seleccionar modulo",
    [
        "Inicio",
        "Estado de datos",
        "Comandos",
        "Roadmap",
    ],
)


def csv_status(name: str) -> dict:
    path = DATA_CLEAN / name
    if not path.exists():
        return {"archivo": name, "estado": "NO EXISTE", "registros": 0}
    try:
        df = pd.read_csv(path)
        return {"archivo": name, "estado": "OK", "registros": len(df)}
    except Exception as exc:
        return {"archivo": name, "estado": f"ERROR: {exc}", "registros": 0}


if modulo == "Inicio":
    st.header("Centro de Comando SIC-BA")
    st.write("Sistema construido para transformar reportes PDF del ERP Valurq en inteligencia comercial, financiera y gerencial.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Extractor PDF", "v1.1")
    col2.metric("Dashboards", "6")
    col3.metric("Motor de alertas", "Activo")

    st.subheader("Modulos disponibles")
    st.markdown(
        """
        - Financiero: `streamlit run src/dashboard_financiero.py`
        - Comercial: `streamlit run src/dashboard_comercial.py`
        - Compras: `streamlit run src/dashboard_compras.py`
        - Tesoreria: `streamlit run src/dashboard_tesoreria.py`
        - Clientes: `streamlit run src/dashboard_clientes.py`
        - Alertas: `streamlit run src/dashboard_alertas.py`
        """
    )

elif modulo == "Estado de datos":
    st.header("Estado de datos limpios")
    files = [
        "fact_cobros.csv",
        "fact_pagos.csv",
        "fact_cheques.csv",
        "fact_compras.csv",
        "fact_ventas.csv",
        "fact_ventas_producto.csv",
        "score_clientes.csv",
        "alertas.csv",
        "log_carga.csv",
    ]
    status = pd.DataFrame([csv_status(f) for f in files])
    st.dataframe(status, use_container_width=True)

elif modulo == "Comandos":
    st.header("Comandos de operacion")
    st.code("pip install -r requirements.txt", language="bash")
    st.code("python src/main.py", language="bash")
    st.code("python src/score_clientes.py", language="bash")
    st.code("python src/alertas.py", language="bash")
    st.code("streamlit run src/dashboard_financiero.py", language="bash")
    st.code("streamlit run src/dashboard_comercial.py", language="bash")
    st.code("streamlit run src/dashboard_compras.py", language="bash")
    st.code("streamlit run src/dashboard_tesoreria.py", language="bash")
    st.code("streamlit run src/dashboard_clientes.py", language="bash")
    st.code("streamlit run src/dashboard_alertas.py", language="bash")

elif modulo == "Roadmap":
    st.header("Roadmap tecnico")
    st.markdown(
        """
        ### v0.1 Construida
        - Extractor PDF Valurq
        - Dashboard financiero
        - Dashboard comercial
        - Dashboard compras
        - Dashboard tesoreria
        - Dashboard clientes
        - Dashboard alertas

        ### v0.2 Proxima fase
        - Ingesta automatica desde Google Drive
        - Reporte diario por email
        - Integracion con base PostgreSQL
        - Asistente IA con consultas en lenguaje natural

        ### v1.0 Objetivo
        - Web app propia
        - Usuarios y permisos
        - IA gerencial completa
        - Automatizacion de cobranzas
        - Forecast de caja y ventas
        """
    )
