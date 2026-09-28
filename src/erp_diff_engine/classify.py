"""Motor de clasificación de diferencias.

Regla dura (AGENTS.md / SPRINT_001_ERP_DRIFT.md): una diferencia real nunca se
marca EXPECTED por inferencia automática. Solo se marca EXPECTED cuando
coincide con una `ExpectedRule` declarada explícitamente en la configuración
del usuario. Toda otra diferencia recibe UNDOCUMENTED, RISK, CRITICAL o
REQUIRES_HUMAN_REVIEW según una tabla de severidad por defecto (documentada
abajo), que la configuración puede sobrescribir explícitamente.
"""

from __future__ import annotations

from .models import ClassifiedDifference, Classification, Difference, DiffKind, EngineConfig

DEFAULT_SEVERITY: dict[DiffKind, Classification] = {
    DiffKind.SHEET_ADDED: Classification.UNDOCUMENTED,
    DiffKind.SHEET_REMOVED: Classification.CRITICAL,
    DiffKind.SHEET_ORDER_CHANGED: Classification.UNDOCUMENTED,
    DiffKind.COLUMN_ADDED: Classification.UNDOCUMENTED,
    DiffKind.COLUMN_REMOVED: Classification.RISK,
    DiffKind.HEADER_CHANGED: Classification.RISK,
    DiffKind.ROW_ADDED: Classification.UNDOCUMENTED,
    DiffKind.ROW_REMOVED: Classification.RISK,
    DiffKind.VALUE_MODIFIED: Classification.UNDOCUMENTED,
    DiffKind.TYPE_CHANGED: Classification.RISK,
    DiffKind.FORMULA_CHANGED: Classification.RISK,
    DiffKind.FORMULA_CHANGED_SAME_VALUE: Classification.REQUIRES_HUMAN_REVIEW,
    DiffKind.DUPLICATE_KEY: Classification.CRITICAL,
    DiffKind.NULL_IN_KEY: Classification.CRITICAL,
    DiffKind.CONTROL_TOTAL_MISMATCH: Classification.CRITICAL,
}


def classify_difference(diff: Difference, config: EngineConfig) -> ClassifiedDifference:
    for rule in config.expected_rules:
        if rule.matches(diff):
            note = f" ({rule.note})" if rule.note else ""
            return ClassifiedDifference(
                difference=diff,
                classification=Classification.EXPECTED,
                rule_applied=f"expected_rules (config){note}",
            )

    if diff.kind in config.severity_overrides:
        return ClassifiedDifference(
            difference=diff,
            classification=config.severity_overrides[diff.kind],
            rule_applied="severity_overrides (config)",
        )

    base_classification = DEFAULT_SEVERITY.get(diff.kind, Classification.REQUIRES_HUMAN_REVIEW)

    if (
        diff.kind is DiffKind.VALUE_MODIFIED
        and diff.sheet is not None
        and diff.column is not None
        and diff.column in config.sensitive_columns.get(diff.sheet, [])
        and base_classification is Classification.UNDOCUMENTED
    ):
        return ClassifiedDifference(
            difference=diff,
            classification=Classification.RISK,
            rule_applied="sensitive_columns (config)",
        )

    return ClassifiedDifference(
        difference=diff, classification=base_classification, rule_applied="default_severity"
    )


def classify_all(diffs: list[Difference], config: EngineConfig) -> list[ClassifiedDifference]:
    return [classify_difference(diff, config) for diff in diffs]
