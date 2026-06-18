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
    cobros = load_csv('fact_cobros.csv')
    crm = load_csv('crm_clientes.csv')

    clientes = set()
    if not cobros.empty and 'cliente' in cobros.columns:
        clientes.update(cobros['cliente'].dropna().astype(str).unique())
    if not crm.empty and 'cliente' in crm.columns:
        clientes.update(crm['cliente'].dropna().astype(str).unique())

    rows = []
    for cliente in sorted(clientes):
        saldo = 0
        if not cobros.empty and 'cliente' in cobros.columns:
            c = cobros[cobros['cliente'].astype(str) == cliente].copy()
            c['saldo'] = pd.to_numeric(c.get('saldo', 0), errors='coerce').fillna(0)
            saldo = c['saldo'].sum()

        linea = 0
        if not crm.empty and 'cliente' in crm.columns and 'linea_credito' in crm.columns:
            r = crm[crm['cliente'].astype(str) == cliente]
            if not r.empty:
                linea = pd.to_numeric(r.get('linea_credito', 0), errors='coerce').fillna(0).iloc[0]

        if linea == 0:
            if saldo >= 100000000:
                linea = 150000000
            elif saldo >= 50000000:
                linea = 100000000
            elif saldo >= 20000000:
                linea = 50000000
            elif saldo > 0:
                linea = 30000000
            else:
                linea = 10000000

        uso_pct = saldo / linea * 100 if linea else 0
        disponible = linea - saldo
        estado = 'ROJO' if uso_pct >= 90 else 'AMARILLO' if uso_pct >= 70 else 'VERDE'

        rows.append({
            'cliente': cliente,
            'linea_credito': linea,
            'saldo_utilizado': saldo,
            'disponible': disponible,
            'uso_pct': round(uso_pct, 2),
            'estado_credito': estado,
            'accion': 'Bloquear nueva venta a credito' if estado == 'ROJO' else 'Revisar credito' if estado == 'AMARILLO' else 'Operar normal'
        })

    pd.DataFrame(rows).to_csv(DATA_CLEAN / 'lineas_credito.csv', index=False, encoding='utf-8-sig')
    print('Lineas de credito generadas')


if __name__ == '__main__':
    main()
