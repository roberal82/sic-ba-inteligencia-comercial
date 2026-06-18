from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'


def load_csv(name):
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def classify_abc(df, group_col, value_col):
    if df.empty or group_col not in df.columns or value_col not in df.columns:
        return pd.DataFrame()
    d = df.copy()
    d[value_col] = pd.to_numeric(d[value_col], errors='coerce').fillna(0)
    out = d.groupby(group_col, dropna=False)[value_col].sum().sort_values(ascending=False).reset_index()
    total = out[value_col].sum()
    out['participacion_pct'] = out[value_col] / total * 100 if total else 0
    out['acumulado_pct'] = out['participacion_pct'].cumsum()
    out['clase_abc'] = out['acumulado_pct'].apply(lambda x: 'A' if x <= 80 else 'B' if x <= 95 else 'C')
    return out


def main():
    DATA_CLEAN.mkdir(exist_ok=True)
    ventas = load_csv('fact_ventas.csv')
    ventas_producto = load_csv('fact_ventas_producto.csv')
    compras = load_csv('fact_compras.csv')

    if not ventas.empty and 'cliente' in ventas.columns:
        abc_clientes = classify_abc(ventas, 'cliente', 'total_gs')
        abc_clientes.to_csv(DATA_CLEAN / 'abc_clientes.csv', index=False, encoding='utf-8-sig')

    if not ventas_producto.empty and 'producto' in ventas_producto.columns:
        abc_productos = classify_abc(ventas_producto, 'producto', 'total')
        abc_productos.to_csv(DATA_CLEAN / 'abc_productos.csv', index=False, encoding='utf-8-sig')

    if not compras.empty and 'proveedor' in compras.columns:
        abc_proveedores = classify_abc(compras, 'proveedor', 'total')
        abc_proveedores.to_csv(DATA_CLEAN / 'abc_proveedores.csv', index=False, encoding='utf-8-sig')

    print('ABC generado')


if __name__ == '__main__':
    main()
