from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'


def load_csv(name):
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def simple_forecast_monthly(df, date_col, value_col, periods=6):
    if df.empty or date_col not in df.columns or value_col not in df.columns:
        return pd.DataFrame()
    d = df.copy()
    d[date_col] = pd.to_datetime(d[date_col], dayfirst=True, errors='coerce')
    d[value_col] = pd.to_numeric(d[value_col], errors='coerce').fillna(0)
    d = d.dropna(subset=[date_col])
    if d.empty:
        return pd.DataFrame()
    d['mes'] = d[date_col].dt.to_period('M').dt.to_timestamp()
    hist = d.groupby('mes')[value_col].sum().reset_index().sort_values('mes')
    if hist.empty:
        return pd.DataFrame()
    base = hist[value_col].tail(3).mean() if len(hist) >= 3 else hist[value_col].mean()
    last_month = hist['mes'].max()
    future = []
    for i in range(1, periods + 1):
        future.append({'mes': last_month + pd.DateOffset(months=i), value_col: round(base, 2), 'tipo': 'forecast'})
    hist['tipo'] = 'historico'
    return pd.concat([hist, pd.DataFrame(future)], ignore_index=True)


def main():
    DATA_CLEAN.mkdir(exist_ok=True)
    ventas = load_csv('fact_ventas.csv')
    cobros = load_csv('fact_cobros.csv')
    pagos = load_csv('fact_pagos.csv')

    if not ventas.empty and 'total_gs' in ventas.columns:
        f_ventas = simple_forecast_monthly(ventas, 'fecha', 'total_gs')
        f_ventas.to_csv(DATA_CLEAN / 'forecast_ventas.csv', index=False, encoding='utf-8-sig')

    if not cobros.empty and 'saldo' in cobros.columns:
        f_cobros = simple_forecast_monthly(cobros, 'vencimiento', 'saldo')
        f_cobros.to_csv(DATA_CLEAN / 'forecast_cobros.csv', index=False, encoding='utf-8-sig')

    if not pagos.empty and 'saldo' in pagos.columns:
        f_pagos = simple_forecast_monthly(pagos, 'vencimiento', 'saldo')
        f_pagos.to_csv(DATA_CLEAN / 'forecast_pagos.csv', index=False, encoding='utf-8-sig')

    print('Forecast generado')


if __name__ == '__main__':
    main()
