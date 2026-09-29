from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'

st.set_page_config(page_title='SIC-BA Margen Real', layout='wide')
st.title('SIC-BA | Margen Bruto Real')
st.caption('Solo costos asignados con evidencia documental; sin estimación por promedio o similitud')


def load_csv(name):
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


cliente = load_csv('rentabilidad_cliente.csv')
detalle = load_csv('rentabilidad_detalle.csv')
readiness = load_csv('margen_readiness.csv')

if not readiness.empty:
    total = int(pd.to_numeric(readiness.get('facturas_venta', 0), errors='coerce').fillna(0).iloc[0])
    calculables = int(pd.to_numeric(readiness.get('facturas_con_costo_documentado', 0), errors='coerce').fillna(0).iloc[0])
    no_calc = int(pd.to_numeric(readiness.get('facturas_no_calculables', 0), errors='coerce').fillna(0).iloc[0])
else:
    total = calculables = no_calc = 0

if cliente.empty:
    venta = costo = margen_gs = margen_pct = 0
else:
    venta = pd.to_numeric(cliente.get('venta_gs', 0), errors='coerce').fillna(0).sum()
    costo = pd.to_numeric(cliente.get('costo_asignado_documentado', 0), errors='coerce').fillna(0).sum()
    margen_gs = pd.to_numeric(cliente.get('margen_bruto_real_gs', 0), errors='coerce').fillna(0).sum()
    margen_pct = margen_gs / venta * 100 if venta else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric('Facturas venta', total if total else 'N/D')
c2.metric('Con costo documentado', calculables)
c3.metric('Sin costo trazable', no_calc if total else 'N/D')
c4.metric('Cobertura margen real', f'{(calculables / total * 100):.1f}%' if total else 'N/D')

st.divider()
if calculables == 0:
    st.warning('Margen real N/D: no existen asignaciones de costo documentadas suficientes.')
else:
    m1, m2, m3 = st.columns(3)
    m1.metric('Venta cubierta', f'Gs {venta:,.0f}')
    m2.metric('Costo documentado', f'Gs {costo:,.0f}')
    m3.metric('Margen bruto real', f'Gs {margen_gs:,.0f} | {margen_pct:.1f}%')

st.subheader('Margen real por cliente')
if cliente.empty:
    st.info('Sin clientes con costo documentado.')
else:
    st.dataframe(cliente, use_container_width=True)
    fig = px.bar(
        cliente.head(15), x='margen_bruto_real_gs', y='cliente', orientation='h',
        title='Top clientes por margen bruto documentado'
    )
    st.plotly_chart(fig, use_container_width=True)

st.subheader('Detalle por factura')
if detalle.empty:
    st.info('Sin facturas con ASIGNACION_COSTO documentada.')
else:
    st.dataframe(detalle.head(200), use_container_width=True)

st.info('Margen por producto permanece N/D hasta existir asignación de costo documental a nivel de producto/ítem.')
