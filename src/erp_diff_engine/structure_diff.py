"""Diferencias estructurales: hojas, columnas y encabezados.

Límite conocido (documentado, no oculto): la detección de columna
agregada/eliminada y encabezado modificado usa emparejamiento por *nombre* de
encabezado (con desambiguación posicional para renombres 1:1). La inserción de
una columna nueva en medio de otras con nombres que ya existían más adelante en
la misma hoja puede no distinguirse perfectamente de un renombrado en cadena.
Ver `risk_report.md` (sección "Limitaciones") para el detalle.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import Difference, DiffKind, SheetSnapshot, WorkbookSnapshot


def _header_key(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _header_quality_diffs(
    sheet_name: str, headers: list[Any], source: str
) -> tuple[list[Difference], dict]:
    """Reporta encabezados vacíos o duplicados sin fingir que son un match único."""

    positions_by_name: dict[str, list[int]] = defaultdict(list)
    empty_positions: list[int] = []
    for position, header in enumerate(headers, start=1):
        key = _header_key(header)
        if key is None:
            empty_positions.append(position)
        else:
            positions_by_name[key].append(position)

    diffs: list[Difference] = []
    for position in empty_positions:
        diffs.append(
            Difference(
                kind=DiffKind.EMPTY_HEADER,
                sheet=sheet_name,
                location=(
                    f"Hoja '{sheet_name}', encabezado vacío en {source}, columna {position}"
                ),
                base_value=position if source == "BASE" else None,
                current_value=position if source == "CURRENT" else None,
                detail="Una columna sin nombre no puede emparejarse documentalmente.",
            )
        )

    duplicates = {
        name: positions
        for name, positions in positions_by_name.items()
        if len(positions) > 1
    }
    for name, positions in duplicates.items():
        diffs.append(
            Difference(
                kind=DiffKind.DUPLICATE_HEADER,
                sheet=sheet_name,
                column=name,
                location=f"Hoja '{sheet_name}', encabezado duplicado en {source}: '{name}'",
                base_value=positions if source == "BASE" else None,
                current_value=positions if source == "CURRENT" else None,
                detail=(
                    f"Columnas {positions}; el motor compara por nombre y no puede "
                    "afirmar una correspondencia única."
                ),
            )
        )
    return diffs, {"empty_positions": empty_positions, "duplicates": duplicates}


def diff_sheets(base: WorkbookSnapshot, current: WorkbookSnapshot) -> tuple[list[Difference], dict]:
    base_set = set(base.sheet_names)
    current_set = set(current.sheet_names)

    sheets_added = [s for s in current.sheet_names if s not in base_set]
    sheets_removed = [s for s in base.sheet_names if s not in current_set]

    common_base_order = [s for s in base.sheet_names if s in current_set]
    common_current_order = [s for s in current.sheet_names if s in base_set]
    order_changed = common_base_order != common_current_order

    diffs: list[Difference] = []
    for name in sheets_added:
        diffs.append(
            Difference(
                kind=DiffKind.SHEET_ADDED,
                sheet=name,
                location=f"Hoja agregada: '{name}'",
                current_value=name,
            )
        )
    for name in sheets_removed:
        diffs.append(
            Difference(
                kind=DiffKind.SHEET_REMOVED,
                sheet=name,
                location=f"Hoja eliminada: '{name}'",
                base_value=name,
            )
        )
    if order_changed:
        diffs.append(
            Difference(
                kind=DiffKind.SHEET_ORDER_CHANGED,
                sheet=None,
                location="Orden de hojas comunes a BASE y CURRENT",
                base_value=common_base_order,
                current_value=common_current_order,
                detail="El orden relativo de las hojas presentes en ambos archivos cambió.",
            )
        )

    summary = {
        "sheets_base": list(base.sheet_names),
        "sheets_current": list(current.sheet_names),
        "sheets_added": sheets_added,
        "sheets_removed": sheets_removed,
        "sheets_common": common_base_order,
        "sheet_order_changed": order_changed,
    }
    return diffs, summary


def diff_columns_and_headers(
    sheet_name: str, base_sheet: SheetSnapshot, current_sheet: SheetSnapshot
) -> tuple[list[Difference], dict]:
    base_headers = list(base_sheet.headers)
    current_headers = list(current_sheet.headers)

    base_named: dict[str, int] = {}
    for pos, header in enumerate(base_headers):
        k = _header_key(header)
        if k is not None and k not in base_named:
            base_named[k] = pos

    current_named: dict[str, int] = {}
    for pos, header in enumerate(current_headers):
        k = _header_key(header)
        if k is not None and k not in current_named:
            current_named[k] = pos

    diffs: list[Difference] = []
    base_quality_diffs, base_quality = _header_quality_diffs(
        sheet_name, base_headers, "BASE"
    )
    current_quality_diffs, current_quality = _header_quality_diffs(
        sheet_name, current_headers, "CURRENT"
    )
    diffs.extend(base_quality_diffs)
    diffs.extend(current_quality_diffs)
    renamed_base_keys: set[str] = set()
    renamed_current_keys: set[str] = set()

    min_len = min(len(base_headers), len(current_headers))
    for pos in range(min_len):
        bk = _header_key(base_headers[pos])
        ck = _header_key(current_headers[pos])
        if bk == ck:
            continue
        explained_elsewhere = (bk is not None and bk in current_named) or (
            ck is not None and ck in base_named
        )
        if explained_elsewhere:
            continue
        diffs.append(
            Difference(
                kind=DiffKind.HEADER_CHANGED,
                sheet=sheet_name,
                location=f"Hoja '{sheet_name}', encabezado columna {pos + 1}",
                column=bk or ck,
                base_value=base_headers[pos],
                current_value=current_headers[pos],
            )
        )
        if bk is not None:
            renamed_base_keys.add(bk)
        if ck is not None:
            renamed_current_keys.add(ck)

    columns_added = [
        k for k in current_named if k not in base_named and k not in renamed_current_keys
    ]
    columns_removed = [
        k for k in base_named if k not in current_named and k not in renamed_base_keys
    ]

    for k in columns_added:
        diffs.append(
            Difference(
                kind=DiffKind.COLUMN_ADDED,
                sheet=sheet_name,
                column=k,
                location=f"Hoja '{sheet_name}', columna agregada '{k}'",
                current_value=k,
            )
        )
    for k in columns_removed:
        diffs.append(
            Difference(
                kind=DiffKind.COLUMN_REMOVED,
                sheet=sheet_name,
                column=k,
                location=f"Hoja '{sheet_name}', columna eliminada '{k}'",
                base_value=k,
            )
        )

    summary = {
        "base_row_count": base_sheet.n_rows,
        "current_row_count": current_sheet.n_rows,
        "base_col_count": base_sheet.n_cols,
        "current_col_count": current_sheet.n_cols,
        "columns_added": columns_added,
        "columns_removed": columns_removed,
        "headers_changed": [
            {"column": d.column, "base": d.base_value, "current": d.current_value}
            for d in diffs
            if d.kind is DiffKind.HEADER_CHANGED
        ],
        "header_quality_base": base_quality,
        "header_quality_current": current_quality,
    }
    return diffs, summary
