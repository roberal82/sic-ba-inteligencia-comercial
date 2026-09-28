from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'

st.set_page_config(page_title='SIC-BA Cotizaciones', layout='wide')
st.title('SIC-BA | Pipeline Comercial')
st.caption('Separación estricta entre sugerencias, oportunidades y forecast documentado')

path = DATA_CLEAN / 'pipeline_cotizaciones.csv'
if not path.exists():
    st.warning('No existe pipeline_cotizaciones.csv. Ejecutar: python src/cotizaciones.py')
    st.stop()

df = pd.read_csv(path)
if df.empty:
    st.info('Sin registros en pipeline')
    st.stop()

# Compatibilidad con archivos anteriores: por defecto ningún registro es apto para forecast.
for col, default in {
    'monto_estimado': pd.NA,
    'probabilidad_pct': pd.NA,
    'monto_fuente': 'NO_DOCUMENTADO',
    'probabilidad_fuente': 'NO_DOCUMENTADA',
    'forecast_elegible': False,
}.items():
    if col not in df.columns:
        df[col] = default

df['monto_estimado_num'] = pd.to_numeric(df['monto_estimado'], errors='coerce')
df['probabilidad_pct_num'] = pd.to_numeric(df['probabilidad_pct'], errors='coerce')

if df['forecast_elegible'].dtype == bool:
    eligible_flag = df['forecast_elegible']
else:
    eligible_flag = (
        df['forecast_elegible']
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({'true', '1', 'si', 'sí'})
    )

df['forecast_documentado'] = (
    eligible_flag
    & df['monto_estimado_num'].notna()
    & df['probabilidad_pct_num'].notna()
    & df['monto_fuente'].astype(str).str.upper().eq('DOCUMENTADO')
    & df['probabilidad_fuente'].astype(str).str.upper().eq('DOCUMENTADA')
)

df['monto_ponderado_documentado'] = pd.NA
mask = df['forecast_documentado']
df.loc[mask, 'monto_ponderado_documentado'] = (
    df.loc[mask, 'monto_estimado_num']
    * df.loc[mask, 'probabilidad_pct_num']
    / 100
)

monto_documentado = df.loc[mask, 'monto_estimado_num'].sum()
ponderado_documentado = pd.to_numeric(
    df.loc[mask, 'monto_ponderado_documentado'], errors='coerce'
).sum()
pendientes_evidencia = int((~mask).sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric('Registros comerciales', len(df))
c2.metric(
    'Monto documentado',
    f"Gs {monto_documentado:,.0f}" if mask.any() else 'N/D',
)
c3.metric(
    'Forecast ponderado documentado',
    f"Gs {ponderado_documentado:,.0f}" if mask.any() else 'N/D',
)
c4.metric('Pendientes de evidencia', pendientes_evidencia)

if not mask.all():
    st.warning(
        'Los registros sin monto y probabilidad documentados NO integran el forecast. '
        'Las sugerencias de recompra no son cotizaciones ni ventas esperadas.'
    )

st.divider()

estados = sorted(df['estado'].dropna().unique().tolist()) if 'estado' in df.columns else []
sel = st.multiselect('Estado', estados, default=estados)
view = df.copy()
if sel and 'estado' in view.columns:
    view = view[view['estado'].isin(sel)]

left, right = st.columns(2)
with left:
    estado = df.groupby('estado', dropna=False).size().reset_index(name='registros')
    st.plotly_chart(px.bar(estado, x='estado', y='registros'), use_container_width=True)
with right:
    origen = df.groupby('origen', dropna=False).size().reset_index(name='registros')
    st.plotly_chart(px.bar(origen, x='origen', y='registros'), use_container_width=True)

st.subheader('Pipeline y sugerencias')
orden = ['forecast_documentado', 'monto_estimado_num']
st.dataframe(
    view.sort_values(orden, ascending=[False, False], na_position='last'),
    use_container_width=True,
)

st.subheader('Forecast documentado')
forecast = df[df['forecast_documentado']].copy()
if forecast.empty:
    st.info('No hay registros aptos para forecast ponderado con evidencia documentada.')
else:
    st.dataframe(
        forecast.sort_values('monto_ponderado_documentado', ascending=False),
        use_container_width=True,
    )
