"""Orquestador del ERP_DIFF_ENGINE.

`run(config)` es la única función pública de alto nivel: carga BASE/CURRENT
(solo lectura), calcula todas las diferencias, las clasifica y escribe los
cinco reportes obligatorios de forma atómica dentro de `output_dir`.

No hay escritura sobre BASE/CURRENT ni sobre ninguna ruta fuera de
`output_dir`. Ver `security.py`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .classify import classify_all
from .models import ClassifiedDifference, Difference, EngineConfig, WorkbookSnapshot
from .loader import load_workbook_snapshot
from .report import (
    DEFAULT_LIMITATIONS,
    build_diff_structure,
    build_diff_summary,
    build_formulas_csv,
    build_risk_report_md,
    build_rows_csv,
    write_reports,
)
from .row_diff import count_nulls, diff_rows_keyed, diff_rows_multiset, diff_rows_positional
from .security import EngineInputError, prepare_output_dir, safe_output_path
from .structure_diff import diff_columns_and_headers, diff_sheets
from .totals import diff_control_totals

logger = logging.getLogger("erp_diff_engine")


@dataclass(frozen=True)
class EngineRunResult:
    output_files: dict[str, Path]
    total_differences: int
    counts_by_classification: dict[str, int] = field(default_factory=dict)


def _configure_logging(log_file: Path | None) -> logging.Handler:
    for existing in list(logger.handlers):
        logger.removeHandler(existing)
        existing.close()
    handler: logging.Handler
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    else:
        handler = logging.StreamHandler()
    # Sin timestamp: mismas entradas/configuración producen también un log reproducible.
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return handler


def _diff_one_sheet(
    sheet_name: str, base_snap: WorkbookSnapshot, current_snap: WorkbookSnapshot, config: EngineConfig
) -> tuple[list[Difference], dict]:
    base_sheet = base_snap.sheets[sheet_name]
    current_sheet = current_snap.sheets[sheet_name]

    diffs: list[Difference] = []

    col_diffs, col_summary = diff_columns_and_headers(sheet_name, base_sheet, current_sheet)
    diffs.extend(col_diffs)

    row_match_mode = config.row_match_modes.get(sheet_name)
    pk_headers = config.primary_keys.get(sheet_name)
    if row_match_mode == "multiset":
        multiset_headers = config.multiset_columns.get(sheet_name)
        if not multiset_headers:
            raise EngineInputError(
                f"row_match_modes['{sheet_name}'] = 'multiset' requiere "
                f"multiset_columns['{sheet_name}'] con al menos una columna."
            )
        row_diffs, row_summary = diff_rows_multiset(
            sheet_name, base_sheet, current_sheet, multiset_headers
        )
    elif pk_headers:
        row_diffs, row_summary = diff_rows_keyed(sheet_name, base_sheet, current_sheet, pk_headers)
    else:
        row_diffs, row_summary = diff_rows_positional(sheet_name, base_sheet, current_sheet)
    diffs.extend(row_diffs)

    control_columns = config.control_totals.get(sheet_name)
    if control_columns:
        total_diffs, totals_result = diff_control_totals(
            sheet_name, base_sheet, current_sheet, control_columns
        )
        diffs.extend(total_diffs)
    else:
        totals_result = {}

    nulls_base = count_nulls(base_sheet)
    nulls_current = count_nulls(current_sheet)

    sheet_structure = {
        **col_summary,
        "row_diff_mode": row_summary["mode"],
        "primary_key": row_summary.get("primary_key", []),
        "rows_added": row_summary["rows_added"],
        "rows_removed": row_summary["rows_removed"],
        "rows_modified": row_summary["rows_modified"],
        "row_matching_evidence": row_summary["row_matching_evidence"],
        "nulls_base": nulls_base,
        "nulls_current": nulls_current,
        "control_totals": totals_result,
    }
    if row_summary.get("primary_key_missing_in_base") or row_summary.get(
        "primary_key_missing_in_current"
    ):
        sheet_structure["primary_key_warning"] = (
            "Clave primaria configurada no encontrada en todas las columnas de la hoja; "
            "se usó el subconjunto disponible."
        )

    return diffs, sheet_structure


def run(config: EngineConfig) -> EngineRunResult:
    output_dir = prepare_output_dir(config.output_dir, config.base_path, config.current_path)
    log_file = (
        safe_output_path(output_dir, str(config.log_file))
        if config.log_file is not None
        else None
    )
    handler = _configure_logging(log_file)
    try:
        return _run_prepared(config, output_dir)
    finally:
        logger.removeHandler(handler)
        handler.close()


def _run_prepared(config: EngineConfig, output_dir: Path) -> EngineRunResult:

    logger.info("Cargando BASE...")
    base_snap = load_workbook_snapshot(
        config.base_path, "BASE", config.header_rows, config.data_start_rows
    )
    logger.info("Cargando CURRENT...")
    current_snap = load_workbook_snapshot(
        config.current_path, "CURRENT", config.header_rows, config.data_start_rows
    )

    sheet_diffs, sheets_summary = diff_sheets(base_snap, current_snap)
    all_diffs: list[Difference] = list(sheet_diffs)

    per_sheet_structure: dict[str, dict] = {}
    for sheet_name in sheets_summary["sheets_common"]:
        diffs, sheet_structure = _diff_one_sheet(
            sheet_name, base_snap, current_snap, config
        )
        all_diffs.extend(diffs)
        per_sheet_structure[sheet_name] = sheet_structure

    for sheet_name in sheets_summary["sheets_removed"]:
        per_sheet_structure[sheet_name] = {
            "only_in": "BASE",
            "base_row_count": base_snap.sheets[sheet_name].n_rows,
            "base_col_count": base_snap.sheets[sheet_name].n_cols,
        }
    for sheet_name in sheets_summary["sheets_added"]:
        per_sheet_structure[sheet_name] = {
            "only_in": "CURRENT",
            "current_row_count": current_snap.sheets[sheet_name].n_rows,
            "current_col_count": current_snap.sheets[sheet_name].n_cols,
        }

    classified: list[ClassifiedDifference] = classify_all(all_diffs, config)

    summary = build_diff_summary(
        base_path=base_snap.path,
        current_path=current_snap.path,
        base_sha256=base_snap.sha256,
        current_sha256=current_snap.sha256,
        sheets_summary=sheets_summary,
        per_sheet=per_sheet_structure,
        classified=classified,
    )
    structure = build_diff_structure(sheets_summary=sheets_summary, per_sheet_structure=per_sheet_structure)
    rows_csv = build_rows_csv(classified)
    formulas_csv = build_formulas_csv(classified)
    risk_report_md = build_risk_report_md(
        base_path=base_snap.path,
        current_path=current_snap.path,
        base_sha256=base_snap.sha256,
        current_sha256=current_snap.sha256,
        sheets_summary=sheets_summary,
        classified=classified,
        limitations=DEFAULT_LIMITATIONS,
    )

    output_files = write_reports(
        output_dir,
        summary=summary,
        structure=structure,
        rows_csv=rows_csv,
        formulas_csv=formulas_csv,
        risk_report_md=risk_report_md,
    )

    logger.info("Reportes escritos en %s (%d diferencias)", output_dir, len(classified))

    return EngineRunResult(
        output_files=output_files,
        total_differences=len(classified),
        counts_by_classification=summary["counts_by_classification"],
    )
