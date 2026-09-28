"""Tests del motor de clasificación: severidad por defecto y reglas explícitas.

Regla dura a proteger con estos tests: ninguna diferencia real se marca
EXPECTED salvo que coincida con una `ExpectedRule` explícita de la
configuración (AGENTS.md: "Nunca EXPECTED por inferencia automática").
"""

from __future__ import annotations

import unittest

from src.erp_diff_engine.classify import classify_all, classify_difference
from src.erp_diff_engine.models import (
    Classification,
    Difference,
    DiffKind,
    EngineConfig,
    ExpectedRule,
)


def _config(**kwargs) -> EngineConfig:
    return EngineConfig(base_path="BASE.xlsx", current_path="CURRENT.xlsx", output_dir="out", **kwargs)


class ClassifyDefaultsTests(unittest.TestCase):
    def test_sheet_removed_is_critical_by_default(self) -> None:
        diff = Difference(kind=DiffKind.SHEET_REMOVED, sheet="X", location="loc")
        result = classify_difference(diff, _config())
        self.assertEqual(result.classification, Classification.CRITICAL)
        self.assertEqual(result.rule_applied, "default_severity")

    def test_row_added_is_undocumented_by_default(self) -> None:
        diff = Difference(kind=DiffKind.ROW_ADDED, sheet="X", location="loc")
        result = classify_difference(diff, _config())
        self.assertEqual(result.classification, Classification.UNDOCUMENTED)

    def test_formula_changed_same_value_is_requires_human_review(self) -> None:
        diff = Difference(kind=DiffKind.FORMULA_CHANGED_SAME_VALUE, sheet="X", location="loc")
        result = classify_difference(diff, _config())
        self.assertEqual(result.classification, Classification.REQUIRES_HUMAN_REVIEW)

    def test_no_diff_kind_is_ever_expected_without_explicit_rule(self) -> None:
        config = _config()
        for kind in DiffKind:
            diff = Difference(kind=kind, sheet="X", location="loc")
            result = classify_difference(diff, config)
            self.assertNotEqual(
                result.classification,
                Classification.EXPECTED,
                msg=f"{kind} no debe ser EXPECTED sin regla explícita",
            )


class ClassifyExpectedRuleTests(unittest.TestCase):
    def test_explicit_expected_rule_matches_only_declared_case(self) -> None:
        config = _config(
            expected_rules=(
                ExpectedRule(kind=DiffKind.SHEET_ADDED, sheet="NUEVA", note="Aprobado"),
            )
        )
        matching = Difference(kind=DiffKind.SHEET_ADDED, sheet="NUEVA", location="loc")
        other_sheet = Difference(kind=DiffKind.SHEET_ADDED, sheet="OTRA", location="loc")
        other_kind = Difference(kind=DiffKind.SHEET_REMOVED, sheet="NUEVA", location="loc")

        self.assertEqual(
            classify_difference(matching, config).classification, Classification.EXPECTED
        )
        self.assertNotEqual(
            classify_difference(other_sheet, config).classification, Classification.EXPECTED
        )
        self.assertNotEqual(
            classify_difference(other_kind, config).classification, Classification.EXPECTED
        )

    def test_expected_rule_can_target_specific_column(self) -> None:
        config = _config(
            expected_rules=(
                ExpectedRule(kind=DiffKind.COLUMN_ADDED, sheet="HOJA", column="Observacion"),
            )
        )
        matching = Difference(
            kind=DiffKind.COLUMN_ADDED, sheet="HOJA", column="Observacion", location="loc"
        )
        other_column = Difference(
            kind=DiffKind.COLUMN_ADDED, sheet="HOJA", column="Otra", location="loc"
        )
        self.assertEqual(
            classify_difference(matching, config).classification, Classification.EXPECTED
        )
        self.assertEqual(
            classify_difference(other_column, config).classification, Classification.UNDOCUMENTED
        )


class ClassifySeverityOverridesTests(unittest.TestCase):
    def test_severity_override_replaces_default(self) -> None:
        config = _config(
            severity_overrides={DiffKind.SHEET_ORDER_CHANGED: Classification.REQUIRES_HUMAN_REVIEW}
        )
        diff = Difference(kind=DiffKind.SHEET_ORDER_CHANGED, sheet=None, location="loc")
        result = classify_difference(diff, config)
        self.assertEqual(result.classification, Classification.REQUIRES_HUMAN_REVIEW)
        self.assertEqual(result.rule_applied, "severity_overrides (config)")

    def test_severity_override_never_produces_expected(self) -> None:
        config = _config(severity_overrides={DiffKind.ROW_ADDED: Classification.RISK})
        diff = Difference(kind=DiffKind.ROW_ADDED, sheet="X", location="loc")
        result = classify_difference(diff, config)
        self.assertEqual(result.classification, Classification.RISK)


class ClassifySensitiveColumnsTests(unittest.TestCase):
    def test_sensitive_column_escalates_value_modified_to_risk(self) -> None:
        config = _config(sensitive_columns={"HOJA": ["Monto"]})
        diff = Difference(
            kind=DiffKind.VALUE_MODIFIED, sheet="HOJA", column="Monto", location="loc"
        )
        result = classify_difference(diff, config)
        self.assertEqual(result.classification, Classification.RISK)

    def test_non_sensitive_column_stays_undocumented(self) -> None:
        config = _config(sensitive_columns={"HOJA": ["Monto"]})
        diff = Difference(
            kind=DiffKind.VALUE_MODIFIED, sheet="HOJA", column="Comentario", location="loc"
        )
        result = classify_difference(diff, config)
        self.assertEqual(result.classification, Classification.UNDOCUMENTED)


class ClassifyAllTests(unittest.TestCase):
    def test_classify_all_preserves_order_and_count(self) -> None:
        diffs = [
            Difference(kind=DiffKind.ROW_ADDED, sheet="X", location="a"),
            Difference(kind=DiffKind.SHEET_REMOVED, sheet="Y", location="b"),
        ]
        results = classify_all(diffs, _config())
        self.assertEqual(len(results), 2)
        self.assertIs(results[0].difference, diffs[0])
        self.assertIs(results[1].difference, diffs[1])


if __name__ == "__main__":
    unittest.main()
