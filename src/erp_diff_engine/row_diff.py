"""Diferencias de filas: agregadas, eliminadas, modificadas, duplicados y nulos.

Tres modos de emparejamiento de filas, seleccionados por `row_match_modes` en
la config (por hoja) o, si no se declara explícitamente, por compatibilidad
histórica (ver `engine._diff_one_sheet`):

- **keyed** (`primary_keys` en la config, por hoja): emparejamiento exacto por
  clave. Es el modo recomendado para hojas transaccionales (ALERTAS,
  SOLICITUDES, etc.). Si se declara explícitamente sin `primary_keys` para esa
  hoja, es un error de configuración (fail closed).
- **positional** (sin clave primaria, o declarado explícitamente aunque exista
  `primary_keys`): emparejamiento posicional robusto a inserciones y
  eliminaciones vía `difflib.SequenceMatcher` sobre la firma normalizada de
  cada fila (usando únicamente las columnas cuyo encabezado existe en ambas
  hojas). Es un fallback razonable, no un sustituto de una clave real.
- **multiset** (requiere declaración explícita + `multiset_columns`):
  comparación como bolsa de firmas normalizadas, pensada para hojas tipo
  log/evento sin clave confiable donde filas idénticas repetidas son válidas.
  Ver `diff_rows_multiset`.

En los tres modos, la comparación celda a celda se hace por *nombre* de
encabezado (no por índice de columna), así que una columna reordenada no
genera falsos "valor modificado".
"""

from __future__ import annotations

import difflib
from collections import defaultdict

from .columns import common_headers as _common_headers_util
from .columns import named_column_index as _named_column_index
from .formula_diff import diff_formulas_for_pair
from .models import Difference, DiffKind, RowRecord, SheetSnapshot
from .normalize import normalize_for_compare, raw_type_label
from .security import EngineInputError


def _common_headers(base_sheet: SheetSnapshot, current_sheet: SheetSnapshot) -> list[str]:
    return _common_headers_util(base_sheet, current_sheet)


def _compare_cells(
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
        base_raw = base_row.values.get(base_cols[header])
        current_raw = current_row.values.get(current_cols[header])
        base_norm = normalize_for_compare(base_raw)
        current_norm = normalize_for_compare(current_raw)
        location = f"Hoja '{sheet_name}', fila {row_key_label}, columna '{header}'"
        if base_norm == current_norm:
            if (
                base_raw is not None
                and current_raw is not None
                and raw_type_label(base_raw) != raw_type_label(current_raw)
            ):
                diffs.append(
                    Difference(
                        kind=DiffKind.TYPE_CHANGED,
                        sheet=sheet_name,
                        column=header,
                        row_key=row_key_label,
                        location=location,
                        base_value=base_raw,
                        current_value=current_raw,
                        detail=(
                            f"Mismo valor normalizado; tipo cambio de "
                            f"{raw_type_label(base_raw)} a {raw_type_label(current_raw)}."
                        ),
                    )
                )
            continue
        diffs.append(
            Difference(
                kind=DiffKind.VALUE_MODIFIED,
                sheet=sheet_name,
                column=header,
                row_key=row_key_label,
                location=location,
                base_value=base_raw,
                current_value=current_raw,
            )
        )
    return diffs


def _compare_pair(
    sheet_name: str,
    common_headers: list[str],
    base_cols: dict[str, int],
    current_cols: dict[str, int],
    base_row: RowRecord,
    current_row: RowRecord,
    row_key_label: str,
) -> tuple[list[Difference], bool]:
    """Compara valores y fórmulas de un par de filas ya emparejadas.

    Devuelve (diferencias, hubo_valor_modificado). Se ejecuta siempre para
    todo par emparejado -incluso si los valores calculados coinciden- porque
    una fórmula puede cambiar sin alterar el valor calculado (item #11).
    """

    cell_diffs = _compare_cells(
        sheet_name, common_headers, base_cols, current_cols, base_row, current_row, row_key_label
    )
    formula_diffs = diff_formulas_for_pair(
        sheet_name, common_headers, base_cols, current_cols, base_row, current_row, row_key_label
    )
    value_modified = any(d.kind is DiffKind.VALUE_MODIFIED for d in cell_diffs)
    return cell_diffs + formula_diffs, value_modified


def _row_key_tuple(row: RowRecord, cols: dict[str, int], pk_headers: list[str]) -> tuple:
    return tuple(normalize_for_compare(row.values.get(cols[h])) for h in pk_headers)


def _stable_key(value: tuple) -> tuple[str, ...]:
    """Orden total reproducible incluso para claves compuestas de tipos mixtos."""

    return tuple(f"{type(component).__name__}:{component!r}" for component in value)


def diff_rows_keyed(
    sheet_name: str,
    base_sheet: SheetSnapshot,
    current_sheet: SheetSnapshot,
    pk_headers: list[str],
) -> tuple[list[Difference], dict]:
    base_cols = _named_column_index(base_sheet)
    current_cols = _named_column_index(current_sheet)
    missing_base = [h for h in pk_headers if h not in base_cols]
    missing_current = [h for h in pk_headers if h not in current_cols]
    if missing_base or missing_current:
        details: list[str] = []
        if missing_base:
            details.append(f"faltan en BASE: {missing_base}")
        if missing_current:
            details.append(f"faltan en CURRENT: {missing_current}")
        raise EngineInputError(
            f"Clave primaria configurada inválida para hoja '{sheet_name}' ("
            + "; ".join(details)
            + ")."
        )

    common_headers = _common_headers(base_sheet, current_sheet)
    diffs: list[Difference] = []

    base_by_key: dict[tuple, list[RowRecord]] = defaultdict(list)
    for row in base_sheet.rows:
        base_by_key[_row_key_tuple(row, base_cols, pk_headers)].append(row)

    current_by_key: dict[tuple, list[RowRecord]] = defaultdict(list)
    for row in current_sheet.rows:
        current_by_key[_row_key_tuple(row, current_cols, pk_headers)].append(row)

    for key, rows in base_by_key.items():
        if any(component is None for component in key):
            diffs.append(
                Difference(
                    kind=DiffKind.NULL_IN_KEY,
                    sheet=sheet_name,
                    row_key=str(key),
                    location=f"Hoja '{sheet_name}', clave primaria con valor nulo en BASE",
                    base_value=key,
                    detail=f"Filas afectadas: {[r.row_number for r in rows]}",
                )
            )
        if len(rows) > 1:
            diffs.append(
                Difference(
                    kind=DiffKind.DUPLICATE_KEY,
                    sheet=sheet_name,
                    row_key=str(key),
                    location=f"Hoja '{sheet_name}', clave primaria duplicada en BASE: {key}",
                    base_value=key,
                    detail=f"Filas duplicadas en BASE: {[r.row_number for r in rows]}",
                )
            )

    for key, rows in current_by_key.items():
        if any(component is None for component in key):
            diffs.append(
                Difference(
                    kind=DiffKind.NULL_IN_KEY,
                    sheet=sheet_name,
                    row_key=str(key),
                    location=f"Hoja '{sheet_name}', clave primaria con valor nulo en CURRENT",
                    current_value=key,
                    detail=f"Filas afectadas: {[r.row_number for r in rows]}",
                )
            )
        if len(rows) > 1:
            diffs.append(
                Difference(
                    kind=DiffKind.DUPLICATE_KEY,
                    sheet=sheet_name,
                    row_key=str(key),
                    location=f"Hoja '{sheet_name}', clave primaria duplicada en CURRENT: {key}",
                    current_value=key,
                    detail=f"Filas duplicadas en CURRENT: {[r.row_number for r in rows]}",
                )
            )

    base_keys = set(base_by_key)
    current_keys = set(current_by_key)

    rows_removed = 0
    rows_added = 0
    rows_modified = 0

    for key in sorted(base_keys - current_keys, key=_stable_key):
        rows_removed += 1
        for row in base_by_key[key]:
            diffs.append(
                Difference(
                    kind=DiffKind.ROW_REMOVED,
                    sheet=sheet_name,
                    row_key=str(key),
                    location=f"Hoja '{sheet_name}', fila eliminada (clave {key}, fila BASE {row.row_number})",
                    base_value=key,
                )
            )

    for key in sorted(current_keys - base_keys, key=_stable_key):
        rows_added += 1
        for row in current_by_key[key]:
            diffs.append(
                Difference(
                    kind=DiffKind.ROW_ADDED,
                    sheet=sheet_name,
                    row_key=str(key),
                    location=f"Hoja '{sheet_name}', fila agregada (clave {key}, fila CURRENT {row.row_number})",
                    current_value=key,
                )
            )

    for key in sorted(base_keys & current_keys, key=_stable_key):
        base_row = base_by_key[key][0]
        current_row = current_by_key[key][0]
        pair_diffs, value_modified = _compare_pair(
            sheet_name, common_headers, base_cols, current_cols, base_row, current_row, str(key)
        )
        if value_modified:
            rows_modified += 1
        diffs.extend(pair_diffs)

    summary = {
        "mode": "keyed",
        "primary_key": pk_headers,
        "primary_key_missing_in_base": missing_base,
        "primary_key_missing_in_current": missing_current,
        "rows_added": rows_added,
        "rows_removed": rows_removed,
        "rows_modified": rows_modified,
        "row_matching_evidence": (
            "REQUIRES_HUMAN_REVIEW"
            if any(d.kind in {DiffKind.DUPLICATE_KEY, DiffKind.NULL_IN_KEY} for d in diffs)
            else "CONFIRMED"
        ),
    }
    return diffs, summary


def diff_rows_multiset(
    sheet_name: str,
    base_sheet: SheetSnapshot,
    current_sheet: SheetSnapshot,
    multiset_headers: list[str],
) -> tuple[list[Difference], dict]:
    """Compara filas como un *multiset* (bolsa) de firmas normalizadas.

    Pensado para hojas tipo log/evento sin clave primaria confiable (hotfix
    Sprint 001, MULTISET_EVENT_MATCHING): filas idénticas repetidas son
    válidas (no DUPLICATE_KEY), el orden no importa (no genera drift), y solo
    se reporta la diferencia *neta* de ocurrencias por firma:
    BASE=2/CURRENT=3 de la misma firma -> +1 ROW_ADDED;
    BASE=3/CURRENT=2 -> -1 ROW_REMOVED. `None` es un componente válido de la
    firma. No hay inferencia semántica ni comparación celda a celda fuera de
    las columnas declaradas: dos filas con firma distinta son, simplemente,
    eventos distintos (nunca se emparejan como "modificación").
    """

    base_cols = _named_column_index(base_sheet)
    current_cols = _named_column_index(current_sheet)
    missing_base = [h for h in multiset_headers if h not in base_cols]
    missing_current = [h for h in multiset_headers if h not in current_cols]
    if missing_base or missing_current:
        details: list[str] = []
        if missing_base:
            details.append(f"faltan en BASE: {missing_base}")
        if missing_current:
            details.append(f"faltan en CURRENT: {missing_current}")
        raise EngineInputError(
            f"multiset_columns configurado inválido para hoja '{sheet_name}' ("
            + "; ".join(details)
            + ")."
        )

    def _signature(row: RowRecord, cols: dict[str, int]) -> tuple:
        return tuple(normalize_for_compare(row.values.get(cols[h])) for h in multiset_headers)

    base_by_sig: dict[tuple, list[RowRecord]] = defaultdict(list)
    for row in base_sheet.rows:
        base_by_sig[_signature(row, base_cols)].append(row)

    current_by_sig: dict[tuple, list[RowRecord]] = defaultdict(list)
    for row in current_sheet.rows:
        current_by_sig[_signature(row, current_cols)].append(row)

    diffs: list[Difference] = []
    rows_added = 0
    rows_removed = 0

    all_signatures = set(base_by_sig) | set(current_by_sig)
    for signature in sorted(all_signatures, key=_stable_key):
        base_rows = base_by_sig.get(signature, [])
        current_rows = current_by_sig.get(signature, [])
        delta = len(current_rows) - len(base_rows)
        if delta > 0:
            rows_added += delta
            for row in current_rows[len(base_rows):]:
                diffs.append(
                    Difference(
                        kind=DiffKind.ROW_ADDED,
                        sheet=sheet_name,
                        row_key=str(signature),
                        location=(
                            f"Hoja '{sheet_name}', ocurrencia agregada (firma multiset "
                            f"{signature}, fila CURRENT {row.row_number})"
                        ),
                        current_value=signature,
                        detail=(
                            f"Ocurrencias BASE={len(base_rows)}, CURRENT={len(current_rows)} "
                            "para esta firma (modo multiset)."
                        ),
                    )
                )
        elif delta < 0:
            rows_removed += -delta
            for row in base_rows[len(current_rows):]:
                diffs.append(
                    Difference(
                        kind=DiffKind.ROW_REMOVED,
                        sheet=sheet_name,
                        row_key=str(signature),
                        location=(
                            f"Hoja '{sheet_name}', ocurrencia eliminada (firma multiset "
                            f"{signature}, fila BASE {row.row_number})"
                        ),
                        base_value=signature,
                        detail=(
                            f"Ocurrencias BASE={len(base_rows)}, CURRENT={len(current_rows)} "
                            "para esta firma (modo multiset)."
                        ),
                    )
                )
        # delta == 0: mismas ocurrencias (incluyendo >1 idénticas): sin drift,
        # nunca DUPLICATE_KEY en modo multiset (regla #8).

    summary = {
        "mode": "multiset",
        "primary_key": [],
        "multiset_columns": multiset_headers,
        "rows_added": rows_added,
        "rows_removed": rows_removed,
        "rows_modified": 0,
        "row_matching_evidence": "CONFIRMED",
    }
    return diffs, summary


def diff_rows_positional(
    sheet_name: str, base_sheet: SheetSnapshot, current_sheet: SheetSnapshot
) -> tuple[list[Difference], dict]:
    base_cols = _named_column_index(base_sheet)
    current_cols = _named_column_index(current_sheet)
    common_headers = _common_headers(base_sheet, current_sheet)

    base_signatures = [
        tuple(normalize_for_compare(row.values.get(base_cols[h])) for h in common_headers)
        for row in base_sheet.rows
    ]
    current_signatures = [
        tuple(normalize_for_compare(row.values.get(current_cols[h])) for h in common_headers)
        for row in current_sheet.rows
    ]

    diffs: list[Difference] = []
    rows_added = 0
    rows_removed = 0
    rows_modified = 0

    matcher = difflib.SequenceMatcher(a=base_signatures, b=current_signatures, autojunk=False)
    opcodes = matcher.get_opcodes()
    has_heuristic_change = any(tag != "equal" for tag, *_ in opcodes)
    if has_heuristic_change:
        diffs.append(
            Difference(
                kind=DiffKind.ROW_MATCH_AMBIGUOUS,
                sheet=sheet_name,
                location=f"Hoja '{sheet_name}', emparejamiento de filas sin clave primaria",
                detail=(
                    "SequenceMatcher produjo una alineación heurística. Las filas agregadas, "
                    "eliminadas o modificadas resultantes son candidatas y requieren una clave "
                    "declarada o revisión humana para confirmar correspondencia documental."
                ),
            )
        )
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            # Los valores normalizados coinciden, pero la fórmula (o el tipo
            # crudo) puede diferir igual: se revisa el par completo (item #11).
            for base_row, current_row in zip(
                base_sheet.rows[i1:i2], current_sheet.rows[j1:j2]
            ):
                label = f"BASE {base_row.row_number} / CURRENT {current_row.row_number}"
                pair_diffs, value_modified = _compare_pair(
                    sheet_name, common_headers, base_cols, current_cols, base_row, current_row, label
                )
                if value_modified:
                    rows_modified += 1
                diffs.extend(pair_diffs)
            continue
        if tag == "delete":
            for row in base_sheet.rows[i1:i2]:
                rows_removed += 1
                diffs.append(
                    Difference(
                        kind=DiffKind.ROW_REMOVED,
                        sheet=sheet_name,
                        row_key=f"fila BASE {row.row_number}",
                        location=f"Hoja '{sheet_name}', fila eliminada (fila BASE {row.row_number})",
                    )
                )
        elif tag == "insert":
            for row in current_sheet.rows[j1:j2]:
                rows_added += 1
                diffs.append(
                    Difference(
                        kind=DiffKind.ROW_ADDED,
                        sheet=sheet_name,
                        row_key=f"fila CURRENT {row.row_number}",
                        location=f"Hoja '{sheet_name}', fila agregada (fila CURRENT {row.row_number})",
                    )
                )
        elif tag == "replace":
            base_block = base_sheet.rows[i1:i2]
            current_block = current_sheet.rows[j1:j2]
            paired = min(len(base_block), len(current_block))
            for offset in range(paired):
                base_row = base_block[offset]
                current_row = current_block[offset]
                label = f"BASE {base_row.row_number} / CURRENT {current_row.row_number}"
                pair_diffs, value_modified = _compare_pair(
                    sheet_name, common_headers, base_cols, current_cols, base_row, current_row, label
                )
                if value_modified:
                    rows_modified += 1
                diffs.extend(pair_diffs)
            for row in base_block[paired:]:
                rows_removed += 1
                diffs.append(
                    Difference(
                        kind=DiffKind.ROW_REMOVED,
                        sheet=sheet_name,
                        row_key=f"fila BASE {row.row_number}",
                        location=f"Hoja '{sheet_name}', fila eliminada (fila BASE {row.row_number})",
                    )
                )
            for row in current_block[paired:]:
                rows_added += 1
                diffs.append(
                    Difference(
                        kind=DiffKind.ROW_ADDED,
                        sheet=sheet_name,
                        row_key=f"fila CURRENT {row.row_number}",
                        location=f"Hoja '{sheet_name}', fila agregada (fila CURRENT {row.row_number})",
                    )
                )

    diffs.extend(_duplicate_signatures(sheet_name, "BASE", base_sheet, base_signatures))
    diffs.extend(_duplicate_signatures(sheet_name, "CURRENT", current_sheet, current_signatures))

    summary = {
        "mode": "positional",
        "primary_key": [],
        "rows_added": rows_added,
        "rows_removed": rows_removed,
        "rows_modified": rows_modified,
        "row_matching_evidence": (
            "INSUFFICIENT_EVIDENCE" if has_heuristic_change else "CANDIDATE"
        ),
    }
    return diffs, summary


def _duplicate_signatures(
    sheet_name: str, source: str, sheet: SheetSnapshot, signatures: list[tuple]
) -> list[Difference]:
    seen: dict[tuple, list[int]] = defaultdict(list)
    for row, signature in zip(sheet.rows, signatures):
        seen[signature].append(row.row_number)

    diffs: list[Difference] = []
    for signature, row_numbers in seen.items():
        if len(row_numbers) > 1 and any(v is not None for v in signature):
            diffs.append(
                Difference(
                    kind=DiffKind.DUPLICATE_KEY,
                    sheet=sheet_name,
                    location=f"Hoja '{sheet_name}', filas duplicadas en {source}: {row_numbers}",
                    detail=f"Contenido repetido (sin clave primaria configurada) en {source}.",
                    base_value=signature if source == "BASE" else None,
                    current_value=signature if source == "CURRENT" else None,
                )
            )
    return diffs


def count_nulls(sheet: SheetSnapshot) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in sheet.rows:
        for col_index, header in enumerate(sheet.headers):
            if header is None:
                continue
            value = row.values.get(col_index)
            if normalize_for_compare(value) is None:
                counts[str(header).strip()] += 1
    return dict(counts)
