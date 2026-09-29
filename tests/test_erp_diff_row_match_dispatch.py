"""Tests del dispatch de ``row_match_modes`` (Sprint 001, Hotfix 5).

Contexto (ver AGENTS.md): revisión independiente detectó que ``engine.py``
solo trataba "multiset" de forma explícita, y trataba "keyed"/"positional"
declarados en ``row_match_modes`` como si no existieran (ambos caían al
`if pk_headers: keyed else: positional`), ignorando el modo declarado
explícitamente en config.py. Este archivo cubre los escenarios A-G del
hotfix: el dispatch debe respetar el modo explícito, con fail-closed para
"keyed" sin `primary_keys`, y solo usar la inferencia histórica
(keyed si hay primary_keys, si no positional) cuando el modo no se declara.

Todos los datos son sintéticos; ningún nombre de hoja, ruta o valor proviene
de Blanco & Asociados ni de ninguna copia real del ERP.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests import erp_diff_fixtures as fx

from src.erp_diff_engine.engine import run
from src.erp_diff_engine.models import EngineConfig
from src.erp_diff_engine.security import EngineInputError


class RowMatchModeDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self._tmp.name)
        self.output_dir = self.base_dir / "output"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, base_sheets: dict, current_sheets: dict, **config_kwargs):
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        fx.write_openpyxl_workbook(base_path, base_sheets)
        fx.write_openpyxl_workbook(current_path, current_sheets)
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            **config_kwargs,
        )
        return run(config)

    def _structure(self) -> dict:
        return json.loads((self.output_dir / "diff_structure.json").read_text(encoding="utf-8"))

    # A. row_match_modes explícito "keyed" + primary_keys configurada -> keyed.
    def test_a_explicit_keyed_with_pk_uses_keyed(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10]]}}
        current = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10], [2, 20]]}}
        self._run(
            base,
            current,
            row_match_modes={"DATOS": "keyed"},
            primary_keys={"DATOS": ["ID"]},
        )
        structure = self._structure()
        self.assertEqual(structure["sheets"]["DATOS"]["row_diff_mode"], "keyed")
        self.assertEqual(structure["sheets"]["DATOS"]["rows_added"], 1)

    # B. row_match_modes explícito "keyed" sin primary_keys -> fail closed.
    def test_b_explicit_keyed_without_pk_fails_closed(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10]]}}
        current = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10], [2, 20]]}}
        with self.assertRaises(EngineInputError):
            self._run(base, current, row_match_modes={"DATOS": "keyed"})

    # C. row_match_modes explícito "positional" + primary_keys existente ->
    # se ignora la clave configurada y se usa positional.
    def test_c_explicit_positional_with_pk_uses_positional(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10], [2, 20]]}}
        current = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10], [3, 99], [2, 20]]}}
        self._run(
            base,
            current,
            row_match_modes={"DATOS": "positional"},
            primary_keys={"DATOS": ["ID"]},
        )
        structure = self._structure()
        self.assertEqual(structure["sheets"]["DATOS"]["row_diff_mode"], "positional")

    # D. row_match_modes explícito "positional" sin primary_keys -> positional.
    def test_d_explicit_positional_without_pk_uses_positional(self) -> None:
        base = {"DATOS": {"headers": ["Nombre", "Valor"], "rows": [["a", 1], ["b", 2]]}}
        current = {"DATOS": {"headers": ["Nombre", "Valor"], "rows": [["a", 1], ["x", 99], ["b", 2]]}}
        self._run(base, current, row_match_modes={"DATOS": "positional"})
        structure = self._structure()
        self.assertEqual(structure["sheets"]["DATOS"]["row_diff_mode"], "positional")

    # E. row_match_modes explícito "multiset" -> multiset (regresión del
    # dispatch existente, ver también test_erp_diff_multiset.py).
    def test_e_explicit_multiset_uses_multiset(self) -> None:
        headers = ["Fecha", "Tipo"]
        rows = [["2024-01-01", "X"], ["2024-01-01", "X"]]
        sheets = {"EVENTOS": {"headers": headers, "rows": rows}}
        result = self._run(
            sheets,
            sheets,
            row_match_modes={"EVENTOS": "multiset"},
            multiset_columns={"EVENTOS": headers},
        )
        structure = self._structure()
        self.assertEqual(structure["sheets"]["EVENTOS"]["row_diff_mode"], "multiset")
        self.assertEqual(result.total_differences, 0)

    # F. row_match_mode no declarado + primary_keys configurada ->
    # compatibilidad histórica: keyed.
    def test_f_undeclared_mode_with_pk_defaults_to_keyed(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10]]}}
        current = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10], [2, 20]]}}
        self._run(base, current, primary_keys={"DATOS": ["ID"]})
        structure = self._structure()
        self.assertEqual(structure["sheets"]["DATOS"]["row_diff_mode"], "keyed")

    # G. row_match_mode no declarado sin primary_keys ->
    # compatibilidad histórica: positional.
    def test_g_undeclared_mode_without_pk_defaults_to_positional(self) -> None:
        base = {"DATOS": {"headers": ["Nombre", "Valor"], "rows": [["a", 1], ["b", 2]]}}
        current = {"DATOS": {"headers": ["Nombre", "Valor"], "rows": [["a", 1], ["x", 99], ["b", 2]]}}
        self._run(base, current)
        structure = self._structure()
        self.assertEqual(structure["sheets"]["DATOS"]["row_diff_mode"], "positional")


if __name__ == "__main__":
    unittest.main()
