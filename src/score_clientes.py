"""
SIC-BA Score de Clientes v0.1
Calcula un score comercial-financiero inicial de 0 a 100.

Entradas esperadas:
- data_clean/fact_ventas.csv
- data_clean/fact_cobros.csv

Salida:
- data_clean/score_clientes.csv
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / "data_clean"


def normalize_score(series: pd.Series, inverse: bool = False) -> pd.Series:
    """Normaliza una serie numérica entre 0 y 100."""
    series = pd.to_numeric(series, errors="coerce").fillna(0)
    min_v = series.min()
    max_v = series.max()
    if max_v == min_v:
        return pd.Series([50] * len(series), index=series.index)
    score = (series - min_v) / (max_v - min_v) * 100
    return 100 - score if inverse else score


def build_score_clientes() -> pd.DataFrame:
    ventas_path = DATA_CLEAN / "fact_ventas.csv"
    cobros_path = DATA_CLEAN / "fact_cobros.csv"

    if not ventas_path.exists() and not cobros_path.exists():
        raise FileNotFoundError("No existen fact_ventas.csv ni fact_cobros.csv en data_clean")

    ventas = pd.read_csv(ventas_path) if ventas_path.exists() else pd.DataFrame()
    cobros = pd.read_csv(cobros_path) if cobros_path.exists() else pd.DataFrame()

    frames = []

    if not ventas.empty:
        ventas["total"] = pd.to_numeric(ventas.get("total", 0), errors="coerce").fillna(0)
        v = ventas.groupby("cliente", dropna=False).agg(
            venta_total=("total", "sum"),
            cantidad_operaciones=("total", "count"),
        )
        frames.append(v)

    if not cobros.empty:
        cobros["saldo"] = pd.to_numeric(cobros.get("saldo", 0), errors="coerce").fillna(0)
        c = cobros.groupby("cliente", dropna=False).agg(
            saldo_pendiente=("saldo", "sum"),
            facturas_pendientes=("saldo", "count"),
        )
        frames.append(c)

    df = pd.concat(frames, axis=1).fillna(0).reset_index()
    df = df.rename(columns={"index": "cliente"})

    df["score_venta"] = normalize_score(df.get("venta_total", 0))
    df["score_frecuencia"] = normalize_score(df.get("cantidad_operaciones", 0))
    df["score_mora"] = normalize_score(df.get("saldo_pendiente", 0), inverse=True)

    df["score_cliente"] = (
        df["score_venta"] * 0.40
        + df["score_frecuencia"] * 0.30
        + df["score_mora"] * 0.30
    ).round(2)

    df["semaforo"] = pd.cut(
        df["score_cliente"],
        bins=[-1, 59.99, 79.99, 100],
        labels=["ROJO", "AMARILLO", "VERDE"],
    )

    return df.sort_values("score_cliente", ascending=False)


if __name__ == "__main__":
    result = build_score_clientes()
    output = DATA_CLEAN / "score_clientes.csv"
    result.to_csv(output, index=False, encoding="utf-8-sig")
    print(f"Score generado: {output}")
