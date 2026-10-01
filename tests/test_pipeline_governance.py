import tempfile
import unittest
from pathlib import Path

import pandas as pd

import src.cotizaciones as cotizaciones
from src.pipeline_governance import apply_forecast_governance, forecast_summary


class PipelineGovernanceTests(unittest.TestCase):
    def test_generated_suggestions_have_no_auto_probability_or_amount(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            old = cotizaciones.DATA_CLEAN
            cotizaciones.DATA_CLEAN = data
            try:
                pd.DataFrame([
                    {"cliente": "CLIENTE A", "monto_referencia": 123456, "accion": "Contactar", "detalle": "Lead"}
                ]).to_csv(data / "oportunidades.csv", index=False)
                pd.DataFrame([
                    {"cliente": "CLIENTE A", "total_gs": 1000000},
                    {"cliente": "CLIENTE B", "total_gs": 500000},
                ]).to_csv(data / "fact_ventas.csv", index=False)

                cotizaciones.main()
                out = pd.read_csv(data / "pipeline_cotizaciones.csv")
            finally:
                cotizaciones.DATA_CLEAN = old

            self.assertTrue(out['probabilidad_pct'].isna().all())
            self.assertTrue(out['monto_estimado'].isna().all())
            self.assertFalse(out['forecast_elegible'].astype(bool).any())
            self.assertTrue(out['id_cotizacion'].isna().all())
            self.assertIn('ventas_historicas_gs', out.columns)

    def test_missing_metadata_is_never_forecast_eligible(self):
        df = pd.DataFrame([
            {"cliente": "A", "monto_estimado": 1000, "probabilidad_pct": 50}
        ])
        governed = apply_forecast_governance(df)
        self.assertFalse(bool(governed.loc[0, 'forecast_documentado']))
        self.assertEqual(forecast_summary(df)['forecast_documentados'], 0)

    def test_only_fully_documented_record_enters_weighted_forecast(self):
        df = pd.DataFrame([
            {
                "cliente": "A",
                "monto_estimado": 1000,
                "probabilidad_pct": 40,
                "monto_fuente": "DOCUMENTADO",
                "probabilidad_fuente": "DOCUMENTADA",
                "forecast_elegible": True,
            },
            {
                "cliente": "B",
                "monto_estimado": 9000,
                "probabilidad_pct": 90,
                "monto_fuente": "NO_DOCUMENTADO",
                "probabilidad_fuente": "NO_DOCUMENTADA",
                "forecast_elegible": True,
            },
        ])
        summary = forecast_summary(df)
        self.assertEqual(summary['forecast_documentados'], 1)
        self.assertEqual(summary['pendientes_evidencia'], 1)
        self.assertEqual(summary['monto_documentado'], 1000.0)
        self.assertEqual(summary['monto_ponderado_documentado'], 400.0)


if __name__ == "__main__":
    unittest.main()
