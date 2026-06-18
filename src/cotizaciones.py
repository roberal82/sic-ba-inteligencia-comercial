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
    oportunidades = load_csv('oportunidades.csv')

    rows = []

    if not oportunidades.empty and 'cliente' in oportunidades.columns:
        for i, r in oportunidades.reset_index().iterrows():
            rows.append({
                'id_cotizacion': f'COT-OP-{i+1:05d}',
                'fecha': pd.Timestamp.today().strftime('%d/%m/%Y'),
                'cliente': r.get('cliente', ''),
                'origen': 'Oportunidad SIC-BA',
                'estado': 'Solicitud',
                'monto_estimado': r.get('monto_referencia', 0),
                'probabilidad_pct': 30,
                'proxima_accion': r.get('accion', 'Preparar cotizacion'),
                'responsable': '',
                'observacion': r.get('detalle', '')
            })

    if not ventas.empty and 'cliente' in ventas.columns:
        ventas['total_gs'] = pd.to_numeric(ventas.get('total_gs', 0), errors='coerce').fillna(0)
        top = ventas.groupby('cliente', dropna=False)['total_gs'].sum().sort_values(ascending=False).head(20).reset_index()
        base = len(rows)
        for i, r in top.iterrows():
            rows.append({
                'id_cotizacion': f'COT-RC-{base+i+1:05d}',
                'fecha': pd.Timestamp.today().strftime('%d/%m/%Y'),
                'cliente': r['cliente'],
                'origen': 'Recompra sugerida',
                'estado': 'Seguimiento',
                'monto_estimado': round(r['total_gs'] * 0.10, 0),
                'probabilidad_pct': 45,
                'proxima_accion': 'Llamar y relevar necesidad de recompra',
                'responsable': '',
                'observacion': 'Cliente de alto volumen'
            })

    df = pd.DataFrame(rows)
    df.to_csv(DATA_CLEAN / 'pipeline_cotizaciones.csv', index=False, encoding='utf-8-sig')
    print('Pipeline de cotizaciones generado')


if __name__ == '__main__':
    main()
