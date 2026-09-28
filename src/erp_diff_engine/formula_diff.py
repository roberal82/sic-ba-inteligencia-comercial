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

        base_value = base_row.values.get(base_col)
        current_value = current_row.values.get(current_col)
        base_cache_status = (
            "CACHE_MISSING"
            if base_formula is not None and base_value is None
            else "PRESENT"
            if base_formula is not None
            else "NOT_APPLICABLE"
        )
        current_cache_status = (
            "CACHE_MISSING"
            if current_formula is not None and current_value is None
            else "PRESENT"
            if current_formula is not None
            else "NOT_APPLICABLE"
        )

        missing_sources = [
            source
            for source, status in (
                ("BASE", base_cache_status),
                ("CURRENT", current_cache_status),
            )
            if status == "CACHE_MISSING"
        ]
        if missing_sources:
            diffs.append(
                Difference(
                    kind=DiffKind.FORMULA_CACHE_MISSING,
                    sheet=sheet_name,
                    column=header,
                    row_key=row_key_label,
                    location=(
                        f"Hoja '{sheet_name}', fila {row_key_label}, columna '{header}', "
                        "valor cacheado ausente"
                    ),
                    base_value=base_formula,
                    current_value=current_formula,
                    base_cached_value=base_value,
                    current_cached_value=current_value,
                    base_cache_status=base_cache_status,
                    current_cache_status=current_cache_status,
                    detail=(
                        f"Sin valor cacheado en {', '.join(missing_sources)}. openpyxl no "
                        "calcula fórmulas; no se infiere ningún resultado calculado."
                    ),
                )
            )

        if base_formula is None and current_formula is None:
            continue
        if base_formula == current_formula:
            continue

        cache_missing = bool(missing_sources)
        same_calculated_value = (
            not cache_missing
            and normalize_for_compare(base_value) == normalize_for_compare(current_value)
        )

        if cache_missing:
            kind = DiffKind.FORMULA_CHANGED_NO_CACHED_VALUE
        elif same_calculated_value:
            kind = DiffKind.FORMULA_CHANGED_SAME_VALUE
        else:
            kind = DiffKind.FORMULA_CHANGED
        location = f"Hoja '{sheet_name}', fila {row_key_label}, columna '{header}'"
        if cache_missing:
            detail = (
                "La fórmula cambió, pero falta al menos un valor cacheado. El motor no "
                "calcula fórmulas y no concluye si el resultado es igual o distinto."
            )
        elif same_calculated_value:
            detail = (
                "Los valores cacheados coinciden pese a que la fórmula es distinta "
                "(posible cambio de lógica oculto)."
            )
        else:
            detail = "La fórmula cambió y los valores cacheados también difieren."
        diffs.append(
            Difference(
                kind=kind,
                sheet=sheet_name,
                column=header,
                row_key=row_key_label,
                location=location,
                base_value=base_formula,
                current_value=current_formula,
                base_cached_value=base_value,
                current_cached_value=current_value,
                base_cache_status=base_cache_status,
                current_cache_status=current_cache_status,
                detail=detail,
            )
        )
    return diffs
