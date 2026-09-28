"""Diferencias de fórmulas por celda.

Se comparan las hojas ya emparejadas (mismo `sheet_name` en BASE y CURRENT).
La comparación de fórmulas es por *nombre de columna* + número de fila de
BASE/CURRENT ya resuelto por `row_diff` (se recibe la lista de pares de filas
emparejadas para no duplicar la lógica de emparejamiento).
"""

from __future__ import annotations

from .models import Difference, DiffKind, RowRecord
from .normalize import normalize_for_compare


def _normalize_formula(formula: str | None) -> str | None:
    if formula is None:
        return None
    return " ".join(formula.strip().split())


def diff_formulas_for_pair(
    sheet_name: str,
    common_headers: list[str],
    base_cols: dict[str, int],
    current_cols: dict[str, int],
    base_row: RowRecord,
    current_row: RowRecord,
    row_key_label: str,
) -> list[Difference]:
    diffs: list[Difference] = []
    for header in common_headers:
        base_col = base_cols[header]
        current_col = current_cols[header]
        base_formula = _normalize_formula(base_row.formulas.get(base_col))
        current_formula = _normalize_formula(current_row.formulas.get(current_col))

        if base_formula is None and current_formula is None:
            continue
        if base_formula == current_formula:
            continue

        base_value = base_row.values.get(base_col)
        current_value = current_row.values.get(current_col)
        same_calculated_value = normalize_for_compare(base_value) == normalize_for_compare(
            current_value
        )

        kind = (
            DiffKind.FORMULA_CHANGED_SAME_VALUE
            if same_calculated_value
            else DiffKind.FORMULA_CHANGED
        )
        location = f"Hoja '{sheet_name}', fila {row_key_label}, columna '{header}'"
        detail = (
            "El valor calculado no cambió pese a que la fórmula es distinta "
            "(posible cambio de lógica oculto)."
            if same_calculated_value
            else "La fórmula cambió y el valor calculado también cambió."
        )
        diffs.append(
            Difference(
                kind=kind,
                sheet=sheet_name,
                column=header,
                row_key=row_key_label,
                location=location,
                base_value=base_formula,
                current_value=current_formula,
                detail=detail,
            )
        )
    return diffs
