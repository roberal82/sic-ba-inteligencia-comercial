"""
SIC-BA Score Comercial de Clientes

Mientras L4 permanezca cerrado, el score se construye únicamente con hechos
comerciales (ventas y frecuencia). No usa saldo pendiente como proxy de mora.
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / "data_clean"


def normalize_score(series: pd.Series) -> pd.Series:
    series = pd.to_numeric(series, errors="coerce").fillna(0)
    min_v = series.min()
    max_v = series.max()
    if len(series) == 0:
        return pd.Series(dtype=float)
    if max_v == min_v:
        return pd.Series([50.0] * len(series), index=series.index)
    return ((series - min_v) / (max_v - min_v) * 100).round(2)


def build_score_clientes(ventas: pd.DataFrame | None = None) -> pd.DataFrame:
    if ventas is None:
        ventas_path = DATA_CLEAN / "fact_ventas.csv"
        if not ventas_path.exists():
            raise FileNotFoundError("No existe fact_ventas.csv en data_clean")
        ventas = pd.read_csv(ventas_path)

    if ventas.empty or 'cliente' not in ventas.columns:
        return pd.DataFrame(columns=[
            'cliente', 'venta_total', 'cantidad_operaciones', 'score_venta',
            'score_frecuencia', 'score_cliente', 'score_tipo', 'segmento_comercial'
        ])

    data = ventas.copy()
    total_col = 'total_gs' if 'total_gs' in data.columns else 'total' if 'total' in data.columns else None
    if total_col is None:
        data['_total'] = 0.0
        total_col = '_total'
    data[total_col] = pd.to_numeric(data[total_col], errors='coerce').fillna(0)

    df = data.groupby("cliente", dropna=False).agg(
        venta_total=(total_col, "sum"),
        cantidad_operaciones=(total_col, "count"),
    ).reset_index()

    df["score_venta"] = normalize_score(df["venta_total"])
    df["score_frecuencia"] = normalize_score(df["cantidad_operaciones"])
    df["score_cliente"] = (
        df["score_venta"] * 0.60 + df["score_frecuencia"] * 0.40
    ).round(2)
    df["score_tipo"] = "COMERCIAL_NO_FINANCIERO"
    df["segmento_comercial"] = pd.cut(
        df["score_cliente"],
        bins=[-1, 49.99, 74.99, 100],
        labels=["C", "B", "A"],
    )
    df["riesgo_credito"] = "N/D"
    df["mora"] = "N/D"
    df["nota_gobierno"] = "Saldo pendiente no equivale a mora; riesgo financiero requiere L4 y vencimiento documentado."

    return df.sort_values("score_cliente", ascending=False)


if __name__ == "__main__":
    result = build_score_clientes()
    output = DATA_CLEAN / "score_clientes.csv"
    result.to_csv(output, index=False, encoding="utf-8-sig")
    print(f"Score comercial generado: {output}")
