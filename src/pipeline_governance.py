from __future__ import annotations

import pandas as pd


def apply_forecast_governance(df: pd.DataFrame) -> pd.DataFrame:
    """Marca forecast solo cuando monto y probabilidad están documentados.

    La ausencia de metadata nunca se interpreta como evidencia ni como 0%.
    """
    out = df.copy()
    for col, default in {
        'monto_estimado': pd.NA,
        'probabilidad_pct': pd.NA,
        'monto_fuente': 'NO_DOCUMENTADO',
        'probabilidad_fuente': 'NO_DOCUMENTADA',
        'forecast_elegible': False,
    }.items():
        if col not in out.columns:
            out[col] = default

    out['monto_estimado_num'] = pd.to_numeric(out['monto_estimado'], errors='coerce')
    out['probabilidad_pct_num'] = pd.to_numeric(out['probabilidad_pct'], errors='coerce')

    if out['forecast_elegible'].dtype == bool:
        eligible_flag = out['forecast_elegible']
    else:
        eligible_flag = (
            out['forecast_elegible']
            .astype(str)
            .str.strip()
            .str.lower()
            .isin({'true', '1', 'si', 'sí'})
        )

    out['forecast_documentado'] = (
        eligible_flag
        & out['monto_estimado_num'].notna()
        & out['probabilidad_pct_num'].notna()
        & out['monto_fuente'].astype(str).str.upper().eq('DOCUMENTADO')
        & out['probabilidad_fuente'].astype(str).str.upper().eq('DOCUMENTADA')
    )

    out['monto_ponderado_documentado'] = pd.NA
    mask = out['forecast_documentado']
    out.loc[mask, 'monto_ponderado_documentado'] = (
        out.loc[mask, 'monto_estimado_num']
        * out.loc[mask, 'probabilidad_pct_num']
        / 100
    )
    return out


def forecast_summary(df: pd.DataFrame) -> dict:
    governed = apply_forecast_governance(df)
    mask = governed['forecast_documentado']
    return {
        'registros': int(len(governed)),
        'forecast_documentados': int(mask.sum()),
        'pendientes_evidencia': int((~mask).sum()),
        'monto_documentado': float(governed.loc[mask, 'monto_estimado_num'].sum()),
        'monto_ponderado_documentado': float(
            pd.to_numeric(
                governed.loc[mask, 'monto_ponderado_documentado'], errors='coerce'
            ).sum()
        ),
    }
