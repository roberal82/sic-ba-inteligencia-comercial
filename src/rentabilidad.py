from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'


def load_csv(name):
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def main():
    DATA_CLEAN.mkdir(exist_ok=True)
    ventas = load_csv('fact_ventas_producto.csv')
    compras = load_csv('fact_compras.csv')

    if ventas.empty:
        print('No existe fact_ventas_producto.csv')
        return

    ventas['total'] = pd.to_numeric(ventas.get('total', 0), errors='coerce').fillna(0)
    ventas['cantidad'] = pd.to_numeric(ventas.get('cantidad', 0), errors='coerce').fillna(0)

    rent = ventas.copy()
    rent['costo_estimado'] = 0.0
    rent['utilidad_estimada'] = 0.0
    rent['margen_estimado_pct'] = 0.0

    if not compras.empty and 'producto' in compras.columns:
        compras['total'] = pd.to_numeric(compras.get('total', 0), errors='coerce').fillna(0)
        compras['cantidad'] = pd.to_numeric(compras.get('cantidad', 0), errors='coerce').fillna(0)
        compras_prod = compras.groupby('producto', dropna=False).agg(
            compra_total=('total', 'sum'),
            compra_cantidad=('cantidad', 'sum')
        ).reset_index()
        compras_prod['costo_unitario_estimado'] = compras_prod.apply(
            lambda r: r['compra_total'] / r['compra_cantidad'] if r['compra_cantidad'] else 0,
            axis=1
        )
        rent = rent.merge(compras_prod[['producto', 'costo_unitario_estimado']], on='producto', how='left')
        rent['costo_unitario_estimado'] = rent['costo_unitario_estimado'].fillna(0)
        rent['costo_estimado'] = rent['cantidad'] * rent['costo_unitario_estimado']
        rent['utilidad_estimada'] = rent['total'] - rent['costo_estimado']
        rent['margen_estimado_pct'] = rent.apply(lambda r: (r['utilidad_estimada'] / r['total'] * 100) if r['total'] else 0, axis=1)

    rent.to_csv(DATA_CLEAN / 'rentabilidad_detalle.csv', index=False, encoding='utf-8-sig')

    if 'cliente' in rent.columns:
        cliente = rent.groupby('cliente', dropna=False).agg(
            venta=('total', 'sum'),
            costo_estimado=('costo_estimado', 'sum'),
            utilidad_estimada=('utilidad_estimada', 'sum')
        ).reset_index()
        cliente['margen_estimado_pct'] = cliente.apply(lambda r: (r['utilidad_estimada'] / r['venta'] * 100) if r['venta'] else 0, axis=1)
        cliente.sort_values('utilidad_estimada', ascending=False).to_csv(DATA_CLEAN / 'rentabilidad_cliente.csv', index=False, encoding='utf-8-sig')

    if 'producto' in rent.columns:
        producto = rent.groupby('producto', dropna=False).agg(
            venta=('total', 'sum'),
            costo_estimado=('costo_estimado', 'sum'),
            utilidad_estimada=('utilidad_estimada', 'sum')
        ).reset_index()
        producto['margen_estimado_pct'] = producto.apply(lambda r: (r['utilidad_estimada'] / r['venta'] * 100) if r['venta'] else 0, axis=1)
        producto.sort_values('utilidad_estimada', ascending=False).to_csv(DATA_CLEAN / 'rentabilidad_producto.csv', index=False, encoding='utf-8-sig')

    print('Rentabilidad generada')


if __name__ == '__main__':
    main()
