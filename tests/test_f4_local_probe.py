import csv
import tempfile
import unittest
from pathlib import Path

from src.orchestration.local_probe import build_local_manifest, csv_has_data


class F4LocalProbeTests(unittest.TestCase):
    def test_csv_has_data_requires_data_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.csv"
            path.write_text("a,b\n", encoding="utf-8")
            self.assertFalse(csv_has_data(path))

            with path.open("a", encoding="utf-8", newline="") as handle:
                csv.writer(handle).writerow(["1", "2"])
            self.assertTrue(csv_has_data(path))

    def test_probe_never_promotes_financial_or_production_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_clean = Path(tmp)
            for filename in [
                "fact_ventas.csv",
                "fact_compras.csv",
                "pipeline_cotizaciones.csv",
            ]:
                (data_clean / filename).write_text("id\n1\n", encoding="utf-8")

            manifest = build_local_manifest(data_clean, run_id="TEST-PROBE")
            self.assertTrue(manifest["inputs"]["sales_ready"])
            self.assertTrue(manifest["inputs"]["purchases_ready"])
            self.assertTrue(manifest["inputs"]["pipeline_ready"])
            self.assertTrue(manifest["inputs"]["bi_ready"])
            self.assertFalse(manifest["inputs"]["cost_evidence_ready"])
            self.assertFalse(manifest["gates"]["l4_pass"])
            self.assertFalse(manifest["gates"]["l7_go"])
            self.assertFalse(manifest["gates"]["human_approval"])


if __name__ == "__main__":
    unittest.main()
