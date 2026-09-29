from pathlib import Path
import pandas as pd

try:
    from src.profitability_governance import build_real_margin, margin_readiness
except ModuleNotFoundError:  # ejecución: python src/rentabilidad.py
    from profitability_governance import build_real_margin, margin_readiness

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'


def load_csv(name):
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def build_outputs(ventas: pd.DataFrame, asignaciones: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    real = build_real_margin(ventas, asignaciones)
    readiness = margin_readiness(ventas, asignaciones)

    if real.empty:
        cliente = pd.DataFrame(columns=['cliente', 'venta_gs', 'costo_asignado_documentado', 'margen_bruto_real_gs', 'margen_bruto_real_pct'])
    else:
        cliente = real.groupby('cliente', dropna=False).agg(
            venta_gs=('venta_gs', 'sum'),
            costo_asignado_documentado=('costo_asignado_documentado', 'sum'),
            margen_bruto_real_gs=('margen_bruto_real_gs', 'sum'),
        ).reset_index()
        cliente['margen_bruto_real_pct'] = (
            cliente['margen_bruto_real_gs'] / cliente['venta_gs'].where(cliente['venta_gs'] != 0) * 100
        ).round(2)
        cliente = cliente.sort_values('margen_bruto_real_gs', ascending=False)

    # Sin asignación de costo a nivel producto no se publica margen por producto.
    producto = pd.DataFrame(columns=[
        'producto', 'venta_gs', 'costo_asignado_documentado',
        'margen_bruto_real_gs', 'margen_bruto_real_pct', 'estado_calidad'
    ])
    return real, cliente, producto, readiness


def main():
    DATA_CLEAN.mkdir(exist_ok=True)
    ventas = load_csv('fact_ventas_producto.csv')
    if ventas.empty:
        ventas = load_csv('fact_ventas.csv')
    asignaciones = load_csv('asignacion_costos.csv')

    if ventas.empty:
        print('No existe fuente de ventas para readiness de margen')
        return

    detalle, cliente, producto, readiness = build_outputs(ventas, asignaciones)
    detalle.to_csv(DATA_CLEAN / 'rentabilidad_detalle.csv', index=False, encoding='utf-8-sig')
    cliente.to_csv(DATA_CLEAN / 'rentabilidad_cliente.csv', index=False, encoding='utf-8-sig')
    producto.to_csv(DATA_CLEAN / 'rentabilidad_producto.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame([readiness]).to_csv(DATA_CLEAN / 'margen_readiness.csv', index=False, encoding='utf-8-sig')

    print(
        'Margen real: '
        f"{readiness['facturas_con_costo_documentado']}/{readiness['facturas_venta']} facturas calculables. "
        'No se estimaron costos por promedio, similitud o cercanía temporal.'
    )


if __name__ == '__main__':
    main()
