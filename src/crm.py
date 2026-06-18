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
    cobros = load_csv('fact_cobros.csv')
    score = load_csv('score_clientes.csv')

    clientes = set()
    for df in [ventas, cobros, score]:
        if not df.empty and 'cliente' in df.columns:
            clientes.update(df['cliente'].dropna().astype(str).unique())

    rows = []
    for cliente in sorted(clientes):
        venta_total = 0
        ultima_compra = ''
        saldo = 0
        sc = 0
        estado = 'ACTIVO'

        if not ventas.empty and 'cliente' in ventas.columns:
            v = ventas[ventas['cliente'].astype(str) == cliente].copy()
            if not v.empty:
                v['total_gs'] = pd.to_numeric(v.get('total_gs', 0), errors='coerce').fillna(0)
                venta_total = v['total_gs'].sum()
                if 'fecha' in v.columns:
                    f = pd.to_datetime(v['fecha'], dayfirst=True, errors='coerce').max()
                    ultima_compra = '' if pd.isna(f) else f.strftime('%d/%m/%Y')

        if not cobros.empty and 'cliente' in cobros.columns:
            c = cobros[cobros['cliente'].astype(str) == cliente].copy()
            if not c.empty:
                c['saldo'] = pd.to_numeric(c.get('saldo', 0), errors='coerce').fillna(0)
                saldo = c['saldo'].sum()

        if not score.empty and 'cliente' in score.columns:
            s = score[score['cliente'].astype(str) == cliente]
            if not s.empty and 'score_cliente' in s.columns:
                sc = float(s['score_cliente'].iloc[0])

        prioridad = 'ALTA' if saldo > 20000000 or venta_total > 50000000 else 'MEDIA' if saldo > 0 or venta_total > 10000000 else 'BAJA'
        proxima_accion = 'Cobrar saldo vencido' if saldo > 0 else 'Visita comercial' if venta_total > 0 else 'Prospectar'

        rows.append({
            'cliente': cliente,
            'venta_total': venta_total,
            'saldo_pendiente': saldo,
            'ultima_compra': ultima_compra,
            'score': sc,
            'estado': estado,
            'prioridad': prioridad,
            'proxima_accion': proxima_accion,
            'responsable': '',
            'telefono': '',
            'email': '',
            'observacion': ''
        })

    pd.DataFrame(rows).to_csv(DATA_CLEAN / 'crm_clientes.csv', index=False, encoding='utf-8-sig')
    print('CRM generado')


if __name__ == '__main__':
    main()
