import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.financial_governance import load_financial_gate
from src.crm import build_crm
from src.score_clientes import build_score_clientes
from src.profitability_governance import build_real_margin, margin_readiness
import src.alertas as alertas


class FinancialGovernanceTests(unittest.TestCase):
    def test_gate_is_fail_closed_when_missing_or_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(load_financial_gate(root).official)

            (root / 'financial_gate.json').write_text(
                json.dumps({'l4_pass': True}), encoding='utf-8'
            )
            self.assertFalse(load_financial_gate(root).official)

            (root / 'financial_gate.json').write_text(
                json.dumps({
                    'l4_pass': True,
                    'cutoff': '2026-09-26T23:59:00-03:00',
                    'approved_by': 'FINANZAS',
                    'evidence_ref': 'L4-CIERRE-VALIDADO',
                }), encoding='utf-8'
            )
            self.assertTrue(load_financial_gate(root).official)

    def test_crm_does_not_turn_provisional_balance_into_collection_action(self):
        ventas = pd.DataFrame([
            {'cliente': 'A', 'total_gs': 60_000_000, 'fecha': '01/09/2026'}
        ])
        cobros = pd.DataFrame([
            {'cliente': 'A', 'saldo': 99_000_000}
        ])
        crm = build_crm(ventas, cobros, pd.DataFrame(), financial_official=False)
        self.assertEqual(crm.loc[0, 'estado_financiero'], 'L4_BLOQUEADO_ND')
        self.assertTrue(pd.isna(crm.loc[0, 'saldo_referencia']))
        self.assertEqual(crm.loc[0, 'prioridad_comercial'], 'ALTA')
        self.assertNotIn('Cobrar', crm.loc[0, 'proxima_accion'])
        self.assertNotIn('vencido', crm.loc[0, 'proxima_accion'].lower())

    def test_score_is_commercial_only_and_has_no_mora_component(self):
        ventas = pd.DataFrame([
            {'cliente': 'A', 'total_gs': 10_000_000},
            {'cliente': 'A', 'total_gs': 5_000_000},
            {'cliente': 'B', 'total_gs': 1_000_000},
        ])
        score = build_score_clientes(ventas)
        self.assertTrue((score['score_tipo'] == 'COMERCIAL_NO_FINANCIERO').all())
        self.assertNotIn('score_mora', score.columns)
        self.assertTrue((score['mora'] == 'N/D').all())
        self.assertTrue((score['riesgo_credito'] == 'N/D').all())

    def test_alerts_ignore_financial_sources_when_l4_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = alertas.DATA_CLEAN
            alertas.DATA_CLEAN = root
            try:
                pd.DataFrame([
                    {'cliente': 'A', 'vencimiento': '01/01/2026', 'saldo': 50_000_000}
                ]).to_csv(root / 'fact_cobros.csv', index=False)
                pd.DataFrame([
                    {'proveedor': 'P', 'vencimiento': '28/09/2026', 'saldo': 10_000_000}
                ]).to_csv(root / 'fact_pagos.csv', index=False)
                pd.DataFrame([
                    {'beneficiario': 'B', 'vencimiento': '28/09/2026', 'monto': 5_000_000}
                ]).to_csv(root / 'fact_cheques.csv', index=False)
                pd.DataFrame([
                    {'cliente': 'A', 'total_gs': 100_000_000}
                ]).to_csv(root / 'fact_ventas.csv', index=False)

                out = alertas.generar_alertas(financial_official=False)
            finally:
                alertas.DATA_CLEAN = old

            modules = set(out['modulo']) if not out.empty else set()
            self.assertNotIn('Cobranza', modules)
            self.assertNotIn('Proveedores', modules)
            self.assertNotIn('Tesorería', modules)

    def test_margin_requires_documented_assignment(self):
        ventas = pd.DataFrame([
            {'factura': '595', 'cliente': 'RECORD', 'total_gs': 5_219_986}
        ])
        bad = pd.DataFrame([
            {
                'factura': '595', 'costo_asignado': 3_000_000,
                'evidencia_ref': '', 'estado_calidad': 'CANDIDATO'
            }
        ])
        self.assertTrue(build_real_margin(ventas, bad).empty)
        self.assertEqual(margin_readiness(ventas, bad)['facturas_con_costo_documentado'], 0)

        good = pd.DataFrame([
            {
                'factura': '595', 'costo_asignado': 3_000_000,
                'evidencia_ref': 'OC/FACTURA/ITEM', 'estado_calidad': 'DOCUMENTADO'
            }
        ])
        real = build_real_margin(ventas, good)
        self.assertEqual(len(real), 1)
        self.assertEqual(real.loc[0, 'margen_bruto_real_gs'], 2_219_986)

    def test_legacy_global_cash_compensation_removed(self):
        source = (Path(__file__).resolve().parents[1] / 'src' / 'dashboard_ceo.py').read_text(encoding='utf-8')
        self.assertNotIn('pendiente_cobro - pendiente_pago - cheques_total', source)
        self.assertIn('Flujo neto permanece N/D', source)

    def test_average_product_cost_inference_removed(self):
        source = (Path(__file__).resolve().parents[1] / 'src' / 'rentabilidad.py').read_text(encoding='utf-8')
        self.assertNotIn('costo_unitario_estimado', source)
        self.assertIn('asignacion_costos.csv', source)


if __name__ == '__main__':
    unittest.main()
