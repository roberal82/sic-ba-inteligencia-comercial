"""Tests de carga de configuración: CLI, archivo JSON y combinación de ambos."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.erp_diff_engine.config import load_config
from src.erp_diff_engine.models import Classification, DiffKind
from src.erp_diff_engine.security import EngineInputError


class LoadConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_config(self, payload: dict) -> Path:
        path = self.base_dir / "config.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_cli_overrides_alone_are_sufficient(self) -> None:
        config = load_config(
            None,
            {
                "base_path": "BASE.xlsx",
                "current_path": "CURRENT.xlsx",
                "output_dir": "out",
                "log_file": None,
            },
        )
        self.assertEqual(str(config.base_path), "BASE.xlsx")
        self.assertEqual(str(config.current_path), "CURRENT.xlsx")

    def test_config_file_alone_is_sufficient(self) -> None:
        config_path = self._write_config(
            {"base_path": "BASE.xlsx", "current_path": "CURRENT.xlsx", "output_dir": "out"}
        )
        config = load_config(config_path, {"base_path": None, "current_path": None, "output_dir": None, "log_file": None})
        self.assertEqual(str(config.output_dir), "out")

    def test_cli_overrides_take_precedence_over_config_file(self) -> None:
        config_path = self._write_config(
            {"base_path": "BASE_CONFIG.xlsx", "current_path": "CURRENT.xlsx", "output_dir": "out"}
        )
        config = load_config(
            config_path,
            {"base_path": "BASE_CLI.xlsx", "current_path": None, "output_dir": None, "log_file": None},
        )
        self.assertEqual(str(config.base_path), "BASE_CLI.xlsx")

    def test_missing_required_paths_raise_controlled_error(self) -> None:
        with self.assertRaises(EngineInputError):
            load_config(None, {"base_path": None, "current_path": None, "output_dir": None})

    def test_primary_keys_and_control_totals_are_parsed(self) -> None:
        config_path = self._write_config(
            {
                "base_path": "BASE.xlsx",
                "current_path": "CURRENT.xlsx",
                "output_dir": "out",
                "primary_keys": {"HOJA": ["ID"]},
                "control_totals": {"HOJA": ["Monto"]},
            }
        )
        config = load_config(config_path, {"base_path": None, "current_path": None, "output_dir": None})
        self.assertEqual(config.primary_keys, {"HOJA": ["ID"]})
        self.assertEqual(config.control_totals, {"HOJA": ["Monto"]})

    def test_expected_rules_are_parsed_into_dataclasses(self) -> None:
        config_path = self._write_config(
            {
                "base_path": "BASE.xlsx",
                "current_path": "CURRENT.xlsx",
                "output_dir": "out",
                "expected_rules": [
                    {"kind": "SHEET_ADDED", "sheet": "NUEVA", "note": "Aprobado"}
                ],
            }
        )
        config = load_config(config_path, {"base_path": None, "current_path": None, "output_dir": None})
        self.assertEqual(len(config.expected_rules), 1)
        self.assertEqual(config.expected_rules[0].kind, DiffKind.SHEET_ADDED)
        self.assertEqual(config.expected_rules[0].sheet, "NUEVA")

    def test_invalid_diff_kind_in_expected_rule_raises_controlled_error(self) -> None:
        config_path = self._write_config(
            {
                "base_path": "BASE.xlsx",
                "current_path": "CURRENT.xlsx",
                "output_dir": "out",
                "expected_rules": [{"kind": "NO_EXISTE"}],
            }
        )
        with self.assertRaises(EngineInputError):
            load_config(config_path, {"base_path": None, "current_path": None, "output_dir": None})

    def test_severity_overrides_are_parsed(self) -> None:
        config_path = self._write_config(
            {
                "base_path": "BASE.xlsx",
                "current_path": "CURRENT.xlsx",
                "output_dir": "out",
                "severity_overrides": {"ROW_ADDED": "RISK"},
            }
        )
        config = load_config(config_path, {"base_path": None, "current_path": None, "output_dir": None})
        self.assertEqual(config.severity_overrides[DiffKind.ROW_ADDED], Classification.RISK)

    def test_severity_override_cannot_assign_expected(self) -> None:
        config_path = self._write_config(
            {
                "base_path": "BASE.xlsx",
                "current_path": "CURRENT.xlsx",
                "output_dir": "out",
                "severity_overrides": {"ROW_ADDED": "EXPECTED"},
            }
        )
        with self.assertRaises(EngineInputError):
            load_config(
                config_path,
                {"base_path": None, "current_path": None, "output_dir": None},
            )

    def test_malformed_json_raises_controlled_error(self) -> None:
        config_path = self.base_dir / "bad.json"
        config_path.write_text("{no es json valido", encoding="utf-8")
        with self.assertRaises(EngineInputError):
            load_config(config_path, {"base_path": None, "current_path": None, "output_dir": None})

    def test_missing_config_file_raises_controlled_error(self) -> None:
        with self.assertRaises(EngineInputError):
            load_config(self.base_dir / "no_existe.json", {"base_path": None, "current_path": None, "output_dir": None})


if __name__ == "__main__":
    unittest.main()
