from __future__ import annotations

import pandas as pd


DOCUMENTED_STATUS = {'DOCUMENTADO', 'VALIDADO_DOCUMENTAL'}


def _invoice_key(df: pd.DataFrame) -> str | None:
    for candidate in ('id_factura_venta', 'factura', 'nro_factura'):
        if candidate in df.columns:
            return candidate
    return None


def build_real_margin(ventas: pd.DataFrame, asignaciones: pd.DataFrame) -> pd.DataFrame:
    """Calcula margen bruto solo con asignaciones documentadas.

    No estima costo por promedio de producto, fecha, proveedor ni similitud.
    """
    columns = [
        'factura_ref', 'cliente', 'venta_gs', 'costo_asignado_documentado',
        'margen_bruto_real_gs', 'margen_bruto_real_pct', 'evidencia_ref',
        'estado_calidad'
    ]
    if ventas.empty or asignaciones.empty:
        return pd.DataFrame(columns=columns)

    v_key = _invoice_key(ventas)
    a_key = _invoice_key(asignaciones)
    required_a = {'costo_asignado', 'evidencia_ref', 'estado_calidad'}
    if v_key is None or a_key is None or not required_a.issubset(asignaciones.columns):
        return pd.DataFrame(columns=columns)

    v = ventas.copy()
    total_col = 'total_gs' if 'total_gs' in v.columns else 'total' if 'total' in v.columns else None
    if total_col is None:
        return pd.DataFrame(columns=columns)
    v[total_col] = pd.to_numeric(v[total_col], errors='coerce')
    v = v[v[total_col].notna()]
    v['factura_ref'] = v[v_key].astype(str).str.strip()

    # Si ventas viene a nivel ítem, la venta se suma por factura.
    group_cols = ['factura_ref']
    if 'cliente' in v.columns:
        group_cols.append('cliente')
    ventas_fact = v.groupby(group_cols, dropna=False)[total_col].sum().reset_index()
    ventas_fact = ventas_fact.rename(columns={total_col: 'venta_gs'})
    if 'cliente' not in ventas_fact.columns:
        ventas_fact['cliente'] = ''

    a = asignaciones.copy()
    a['factura_ref'] = a[a_key].astype(str).str.strip()
    a['costo_asignado'] = pd.to_numeric(a['costo_asignado'], errors='coerce')
    a['estado_calidad_norm'] = a['estado_calidad'].astype(str).str.upper().str.strip()
    a['evidencia_ref'] = a['evidencia_ref'].astype(str).str.strip()
    a = a[
        a['costo_asignado'].notna()
        & (a['costo_asignado'] >= 0)
        & a['estado_calidad_norm'].isin(DOCUMENTED_STATUS)
        & a['evidencia_ref'].ne('')
    ]
    if a.empty:
        return pd.DataFrame(columns=columns)

    costos = a.groupby('factura_ref', dropna=False).agg(
        costo_asignado_documentado=('costo_asignado', 'sum'),
        evidencia_ref=('evidencia_ref', lambda s: ' | '.join(sorted(set(s)))),
    ).reset_index()

    out = ventas_fact.merge(costos, on='factura_ref', how='inner')
    out['margen_bruto_real_gs'] = out['venta_gs'] - out['costo_asignado_documentado']
    out['margen_bruto_real_pct'] = (
        out['margen_bruto_real_gs'] / out['venta_gs'].where(out['venta_gs'] != 0) * 100
    ).round(2)
    out['estado_calidad'] = 'MARGEN_DOCUMENTADO'
    return out[columns].sort_values('margen_bruto_real_gs', ascending=False)


def margin_readiness(ventas: pd.DataFrame, asignaciones: pd.DataFrame) -> dict:
    v_key = _invoice_key(ventas)
    total_facturas = int(ventas[v_key].astype(str).nunique()) if (not ventas.empty and v_key) else 0
    real = build_real_margin(ventas, asignaciones)
    calculables = int(real['factura_ref'].nunique()) if not real.empty else 0
    return {
        'facturas_venta': total_facturas,
        'facturas_con_costo_documentado': calculables,
        'facturas_no_calculables': max(total_facturas - calculables, 0),
    }
