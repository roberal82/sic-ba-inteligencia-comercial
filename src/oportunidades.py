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
    ventas = load_csv('fact_ventas.csv')
    ventas_producto = load_csv('fact_ventas_producto.csv')

    if ventas.empty and ventas_producto.empty:
        print('No hay ventas para detectar oportunidades')
        return

    rows = []
    hoy = pd.Timestamp.today().normalize()

    if not ventas.empty and 'cliente' in ventas.columns and 'fecha' in ventas.columns:
        ventas['fecha_dt'] = pd.to_datetime(ventas['fecha'], dayfirst=True, errors='coerce')
        ventas['total_gs'] = pd.to_numeric(ventas.get('total_gs', 0), errors='coerce').fillna(0)
        resumen = ventas.groupby('cliente', dropna=False).agg(
            venta_total=('total_gs', 'sum'),
            facturas=('total_gs', 'count'),
            ultima_compra=('fecha_dt', 'max')
        ).reset_index()
        resumen['dias_sin_compra'] = (hoy - resumen['ultima_compra']).dt.days
        for _, r in resumen.iterrows():
            if pd.notna(r['dias_sin_compra']) and r['dias_sin_compra'] >= 45:
                rows.append({
                    'cliente': r['cliente'],
                    'tipo_oportunidad': 'Recuperacion',
                    'prioridad': 'ALTA' if r['venta_total'] >= 30000000 else 'MEDIA',
                    'detalle': f"Cliente sin compra hace {int(r['dias_sin_compra'])} dias",
                    'monto_referencia': r['venta_total'],
                    'accion': 'Contactar y ofrecer reposicion o nueva cotizacion'
                })

    if not ventas_producto.empty and {'cliente', 'producto', 'total'}.issubset(ventas_producto.columns):
        ventas_producto['total'] = pd.to_numeric(ventas_producto['total'], errors='coerce').fillna(0)
        cliente_prod = ventas_producto.groupby(['cliente', 'producto'], dropna=False)['total'].sum().reset_index()
        top_prod = ventas_producto.groupby('producto', dropna=False)['total'].sum().sort_values(ascending=False).head(20).index.tolist()
        for cliente in cliente_prod['cliente'].dropna().unique():
            comprados = set(cliente_prod[cliente_prod['cliente'] == cliente]['producto'].dropna().tolist())
            faltantes = [p for p in top_prod if p not in comprados][:3]
            venta_cliente = cliente_prod[cliente_prod['cliente'] == cliente]['total'].sum()
            if faltantes and venta_cliente > 0:
                rows.append({
                    'cliente': cliente,
                    'tipo_oportunidad': 'Venta cruzada',
                    'prioridad': 'MEDIA',
                    'detalle': 'Productos potenciales: ' + ', '.join(map(str, faltantes)),
                    'monto_referencia': venta_cliente,
                    'accion': 'Preparar oferta cruzada sobre productos de alta rotacion'
                })

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(['prioridad', 'monto_referencia'], ascending=[True, False])
    out.to_csv(DATA_CLEAN / 'oportunidades.csv', index=False, encoding='utf-8-sig')
    print('Oportunidades generadas')


if __name__ == '__main__':
    main()
