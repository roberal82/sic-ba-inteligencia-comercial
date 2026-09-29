from pathlib import Path
import pandas as pd

try:
    from src.financial_governance import load_financial_gate
except ModuleNotFoundError:  # ejecución: python src/crm.py
    from financial_governance import load_financial_gate

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / 'data_clean'


def load_csv(name):
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def build_crm(ventas: pd.DataFrame, cobros: pd.DataFrame, score: pd.DataFrame, financial_official: bool = False) -> pd.DataFrame:
    """Construye CRM priorizando hechos comerciales.

    Los saldos solo se exponen como referencia cuando L4 está oficialmente abierto.
    Un saldo positivo nunca se transforma por sí mismo en "vencido" ni en orden de cobro.
    """
    clientes = set()
    for df in [ventas, cobros if financial_official else pd.DataFrame(), score]:
        if not df.empty and 'cliente' in df.columns:
            clientes.update(df['cliente'].dropna().astype(str).unique())

    rows = []
    for cliente in sorted(clientes):
        venta_total = 0.0
        ultima_compra = ''
        saldo_ref = pd.NA
        sc = pd.NA

        if not ventas.empty and 'cliente' in ventas.columns:
            v = ventas[ventas['cliente'].astype(str) == cliente].copy()
            if not v.empty:
                total_col = 'total_gs' if 'total_gs' in v.columns else 'total' if 'total' in v.columns else None
                if total_col:
                    v[total_col] = pd.to_numeric(v[total_col], errors='coerce').fillna(0)
                    venta_total = float(v[total_col].sum())
                if 'fecha' in v.columns:
                    f = pd.to_datetime(v['fecha'], dayfirst=True, errors='coerce').max()
                    ultima_compra = '' if pd.isna(f) else f.strftime('%d/%m/%Y')

        if financial_official and not cobros.empty and 'cliente' in cobros.columns:
            c = cobros[cobros['cliente'].astype(str) == cliente].copy()
            if not c.empty and 'saldo' in c.columns:
                c['saldo'] = pd.to_numeric(c['saldo'], errors='coerce').fillna(0)
                saldo_ref = float(c['saldo'].sum())

        if not score.empty and 'cliente' in score.columns:
            s = score[score['cliente'].astype(str) == cliente]
            if not s.empty and 'score_cliente' in s.columns:
                sc = pd.to_numeric(s['score_cliente'].iloc[0], errors='coerce')

        prioridad = 'ALTA' if venta_total > 50_000_000 else 'MEDIA' if venta_total > 10_000_000 else 'BAJA'
        proxima_accion = 'Gestionar cuenta clave' if prioridad == 'ALTA' else 'Visita comercial' if venta_total > 0 else 'Prospectar'

        rows.append({
            'cliente': cliente,
            'venta_total': venta_total,
            'saldo_referencia': saldo_ref,
            'estado_financiero': 'OFICIAL_L4' if financial_official else 'L4_BLOQUEADO_ND',
            'ultima_compra': ultima_compra,
            'score_comercial': sc,
            'estado': 'ACTIVO',
            'prioridad_comercial': prioridad,
            'proxima_accion': proxima_accion,
            'responsable': '',
            'telefono': '',
            'email': '',
            'observacion': 'Saldo no implica mora; cobranza requiere vencimiento documentado y gate financiero.'
        })

    return pd.DataFrame(rows)


def main():
    DATA_CLEAN.mkdir(exist_ok=True)
    ventas = load_csv('fact_ventas.csv')
    cobros = load_csv('fact_cobros.csv')
    score = load_csv('score_clientes.csv')
    gate = load_financial_gate(DATA_CLEAN)

    crm = build_crm(ventas, cobros, score, financial_official=gate.official)
    crm.to_csv(DATA_CLEAN / 'crm_clientes.csv', index=False, encoding='utf-8-sig')
    print(f'CRM generado | finanzas_oficiales={gate.official}')


if __name__ == '__main__':
    main()
