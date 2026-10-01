from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'


def load_csv(name):
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _base_record(record_id, cliente, origen, estado, accion, observacion=''):
    """Registro comercial no apto para forecast hasta documentar monto/probabilidad."""
    return {
        'id_registro': record_id,
        'id_cotizacion': '',
        'fecha': pd.Timestamp.today().strftime('%d/%m/%Y'),
        'cliente': cliente,
        'origen': origen,
        'estado': estado,
        'monto_estimado': '',
        'probabilidad_pct': '',
        'monto_fuente': 'NO_DOCUMENTADO',
        'probabilidad_fuente': 'NO_DOCUMENTADA',
        'forecast_elegible': False,
        'proxima_accion': accion,
        'responsable': '',
        'observacion': observacion,
    }


def main():
    DATA_CLEAN.mkdir(exist_ok=True)
    ventas = load_csv('fact_ventas.csv')
    oportunidades = load_csv('oportunidades.csv')

    rows = []

    if not oportunidades.empty and 'cliente' in oportunidades.columns:
        for i, r in oportunidades.reset_index().iterrows():
            row = _base_record(
                f'OPP-SIC-{i+1:05d}',
                r.get('cliente', ''),
                'Oportunidad SIC-BA',
                'Solicitud',
                r.get('accion', 'Preparar cotizacion'),
                r.get('detalle', ''),
            )
            # Puede conservarse como referencia analítica, pero nunca como monto de pipeline.
            row['monto_referencia_no_oficial'] = r.get('monto_referencia', '')
            row['regla_referencia'] = 'FUENTE_OPORTUNIDADES / NO OFICIAL'
            rows.append(row)

    if not ventas.empty and 'cliente' in ventas.columns:
        ventas = ventas.copy()
        ventas['total_gs'] = pd.to_numeric(ventas.get('total_gs', 0), errors='coerce').fillna(0)
        top = (
            ventas.groupby('cliente', dropna=False)['total_gs']
            .sum()
            .sort_values(ascending=False)
            .head(20)
            .reset_index()
        )
        base = len(rows)
        for i, r in top.iterrows():
            row = _base_record(
                f'SUG-RC-{base+i+1:05d}',
                r['cliente'],
                'Recompra sugerida',
                'Seguimiento sugerido',
                'Llamar y relevar necesidad de recompra',
                'Sugerencia basada en actividad histórica; no es cotizacion, forecast ni venta esperada.',
            )
            # Dato factual de contexto. No se calcula 10%, monto esperado ni probabilidad.
            row['ventas_historicas_gs'] = round(float(r['total_gs']), 0)
            row['monto_referencia_no_oficial'] = ''
            row['regla_referencia'] = 'SIN MONTO SUGERIDO / REQUIERE EVIDENCIA COMERCIAL'
            rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(DATA_CLEAN / 'pipeline_cotizaciones.csv', index=False, encoding='utf-8-sig')
    print('Pipeline comercial generado sin probabilidad ni forecast inferidos')


if __name__ == '__main__':
    main()
