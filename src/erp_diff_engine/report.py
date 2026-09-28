"""Construcción y escritura atómica de los reportes obligatorios.

Salidas (siempre dentro de `output_dir`, nunca fuera):
- diff_summary.json   — resumen agregado + metadata de auditoría (SHA-256).
- diff_structure.json — hojas, columnas y encabezados.
- diff_rows.csv       — filas/celdas: agregadas, eliminadas, valores, duplicados, nulos, totales.
- diff_formulas.csv   — cambios de fórmula.
- risk_report.md      — reporte humano, agrupado por severidad.

Reproducibilidad: ningún reporte incluye timestamps de ejecución. Las mismas
entradas + misma configuración deben producir bytes idénticos (idempotencia).
"""

from __future__ import annotations

import csv
import datetime
import io
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from . import __version__
from .models import ClassifiedDifference, Classification, CLASSIFICATION_SEVERITY, DiffKind
from .security import atomic_write_text, safe_output_path

STRUCTURE_KINDS = {
    DiffKind.SHEET_ADDED,
    DiffKind.SHEET_REMOVED,
    DiffKind.SHEET_ORDER_CHANGED,
    DiffKind.COLUMN_ADDED,
    DiffKind.COLUMN_REMOVED,
    DiffKind.HEADER_CHANGED,
    DiffKind.DUPLICATE_HEADER,
    DiffKind.EMPTY_HEADER,
}
FORMULA_KINDS = {
    DiffKind.FORMULA_CHANGED,
    DiffKind.FORMULA_CHANGED_SAME_VALUE,
    DiffKind.FORMULA_CHANGED_NO_CACHED_VALUE,
    DiffKind.FORMULA_CACHE_MISSING,
}
ROW_KINDS = {
    DiffKind.ROW_ADDED,
    DiffKind.ROW_REMOVED,
    DiffKind.ROW_MATCH_AMBIGUOUS,
    DiffKind.VALUE_MODIFIED,
    DiffKind.TYPE_CHANGED,
    DiffKind.DUPLICATE_KEY,
    DiffKind.NULL_IN_KEY,
    DiffKind.CONTROL_TOTAL_MISMATCH,
    DiffKind.CONTROL_TOTAL_COLUMN_MISSING,
    DiffKind.CONTROL_TOTAL_INVALID_VALUE,
}

FILENAMES = {
    "summary": "diff_summary.json",
    "structure": "diff_structure.json",
    "rows_csv": "diff_rows.csv",
    "formulas_csv": "diff_formulas.csv",
    "risk_report": "risk_report.md",
}


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, (Classification, DiffKind)):
        return obj.value
    if isinstance(obj, (set, tuple)):
        return list(obj)
    return str(obj)


def _cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def build_diff_summary(
    *,
    base_path: Path,
    current_path: Path,
    base_sha256: str,
    current_sha256: str,
    sheets_summary: dict,
    per_sheet: dict[str, dict],
    classified: list[ClassifiedDifference],
) -> dict:
    counts_by_kind: dict[str, int] = {}
    counts_by_classification: dict[str, int] = {c.value: 0 for c in Classification}
    for item in classified:
        counts_by_kind[item.difference.kind.value] = (
            counts_by_kind.get(item.difference.kind.value, 0) + 1
        )
        counts_by_classification[item.classification.value] += 1

    return {
        "engine_version": __version__,
        "base_path": str(base_path),
        "current_path": str(current_path),
        "base_sha256": base_sha256,
        "current_sha256": current_sha256,
        "sheets": sheets_summary,
        "per_sheet": per_sheet,
        "total_differences": len(classified),
        "counts_by_kind": counts_by_kind,
        "counts_by_classification": counts_by_classification,
        "classification_policy": (
            "Ninguna diferencia se clasifica EXPECTED por inferencia automática. "
            "EXPECTED solo aplica si coincide con una regla explícita de configuración."
        ),
    }


def build_diff_structure(
    *, sheets_summary: dict, per_sheet_structure: dict[str, dict]
) -> dict:
    return {
        "sheets_base": sheets_summary["sheets_base"],
        "sheets_current": sheets_summary["sheets_current"],
        "sheets_added": sheets_summary["sheets_added"],
        "sheets_removed": sheets_summary["sheets_removed"],
        "sheet_order_changed": sheets_summary["sheet_order_changed"],
        "sheets": per_sheet_structure,
    }


def build_rows_csv(classified: list[ClassifiedDifference]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "sheet",
            "kind",
            "row_key",
            "column",
            "base_value",
            "current_value",
            "classification",
            "rule_applied",
            "detail",
            "location",
        ]
    )
    for item in classified:
        if item.difference.kind not in ROW_KINDS:
            continue
        d = item.difference
        writer.writerow(
            [
                _cell(d.sheet),
                d.kind.value,
                _cell(d.row_key),
                _cell(d.column),
                _cell(d.base_value),
                _cell(d.current_value),
                item.classification.value,
                item.rule_applied,
                d.detail,
                d.location,
            ]
        )
    return buffer.getvalue()


def build_formulas_csv(classified: list[ClassifiedDifference]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "sheet",
            "kind",
            "row_key",
            "column",
            "base_formula",
            "current_formula",
            "base_cached_value",
            "current_cached_value",
            "base_cache_status",
            "current_cache_status",
            "classification",
            "rule_applied",
            "detail",
            "location",
        ]
    )
    for item in classified:
        if item.difference.kind not in FORMULA_KINDS:
            continue
        d = item.difference
        writer.writerow(
            [
                _cell(d.sheet),
                d.kind.value,
                _cell(d.row_key),
                _cell(d.column),
                _cell(d.base_value),
                _cell(d.current_value),
                _cell(d.base_cached_value),
                _cell(d.current_cached_value),
                d.base_cache_status,
                d.current_cache_status,
                item.classification.value,
                item.rule_applied,
                d.detail,
                d.location,
            ]
        )
    return buffer.getvalue()


_SEVERITY_ORDER = sorted(Classification, key=lambda c: CLASSIFICATION_SEVERITY[c], reverse=True)
_MAX_ITEMS_PER_SECTION = 50


def build_risk_report_md(
    *,
    base_path: Path,
    current_path: Path,
    base_sha256: str,
    current_sha256: str,
    sheets_summary: dict,
    classified: list[ClassifiedDifference],
    limitations: list[str],
) -> str:
    lines: list[str] = []
    lines.append("# Risk Report — ERP_DIFF_ENGINE")
    lines.append("")
    lines.append(f"- BASE: `{base_path}` (SHA-256 `{base_sha256}`)")
    lines.append(f"- CURRENT: `{current_path}` (SHA-256 `{current_sha256}`)")
    lines.append(f"- Hojas BASE: {len(sheets_summary['sheets_base'])}")
    lines.append(f"- Hojas CURRENT: {len(sheets_summary['sheets_current'])}")
    lines.append(f"- Hojas agregadas: {sheets_summary['sheets_added'] or 'ninguna'}")
    lines.append(f"- Hojas eliminadas: {sheets_summary['sheets_removed'] or 'ninguna'}")
    lines.append(f"- Orden de hojas cambiado: {sheets_summary['sheet_order_changed']}")
    lines.append(f"- Total de diferencias detectadas: {len(classified)}")
    lines.append("")
    lines.append(
        "> Política de clasificación: ninguna diferencia real se marca `EXPECTED` "
        "por inferencia automática. Solo se marca `EXPECTED` cuando coincide con una "
        "regla explícita declarada en la configuración."
    )
    lines.append("")

    by_classification: dict[Classification, list[ClassifiedDifference]] = {
        c: [] for c in Classification
    }
    for item in classified:
        by_classification[item.classification].append(item)

    for classification in _SEVERITY_ORDER:
        items = by_classification[classification]
        lines.append(f"## {classification.value} ({len(items)})")
        lines.append("")
        if not items:
            lines.append("_Sin hallazgos._")
            lines.append("")
            continue
        for item in items[:_MAX_ITEMS_PER_SECTION]:
            d = item.difference
            lines.append(f"- **{d.kind.value}** — {d.location} — regla: `{item.rule_applied}`")
            if d.detail:
                lines.append(f"  - {d.detail}")
        if len(items) > _MAX_ITEMS_PER_SECTION:
            remaining = len(items) - _MAX_ITEMS_PER_SECTION
            lines.append(
                f"- … y {remaining} más. Ver `diff_rows.csv`, `diff_formulas.csv` "
                "o `diff_structure.json`."
            )
        lines.append("")

    lines.append("## Limitaciones conocidas")
    lines.append("")
    for limitation in limitations:
        lines.append(f"- {limitation}")
    lines.append("")

    return "\n".join(lines) + "\n"


DEFAULT_LIMITATIONS = [
    "La detección de columna agregada/eliminada y encabezado modificado usa "
    "emparejamiento por nombre de encabezado con desambiguación posicional para "
    "renombres 1:1; una inserción de columna en medio de encabezados que ya "
    "existían más adelante puede no distinguirse perfectamente de un renombrado.",
    "Sin clave primaria configurada para una hoja, el emparejamiento de filas es "
    "posicional (SequenceMatcher) y es un fallback razonable, no un sustituto de "
    "una clave real declarada en 'primary_keys'.",
    "El valor calculado de una fórmula (data_only=True) depende de que el "
    "archivo Excel tenga el valor cacheado (guardado por Excel/LibreOffice). "
    "openpyxl no calcula fórmulas. La ausencia de caché se reporta de forma "
    "explícita y nunca se interpreta como igualdad de resultados; un caché "
    "presente también puede estar obsoleto y el motor no certifica su frescura.",
    "Los encabezados duplicados o vacíos se reportan como hallazgos de riesgo, "
    "pero sus columnas no tienen una correspondencia documental única y el "
    "contenido completo de esas columnas requiere revisión humana.",
    "Excel/openpyxl puede serializar un float integral como entero; si el tipo "
    "original no sobrevive a la lectura, el motor no puede reconstruirlo.",
    "Los totales de control solo se calculan para columnas declaradas "
    "explícitamente en 'control_totals'; no se infieren automáticamente.",
]


def write_reports(
    output_dir: Path,
    *,
    summary: dict,
    structure: dict,
    rows_csv: str,
    formulas_csv: str,
    risk_report_md: str,
) -> dict[str, Path]:
    written: dict[str, Path] = {}

    summary_path = safe_output_path(output_dir, FILENAMES["summary"])
    atomic_write_text(
        summary_path, json.dumps(summary, default=_json_default, ensure_ascii=False, indent=2, sort_keys=True)
    )
    written["summary"] = summary_path

    structure_path = safe_output_path(output_dir, FILENAMES["structure"])
    atomic_write_text(
        structure_path,
        json.dumps(structure, default=_json_default, ensure_ascii=False, indent=2, sort_keys=True),
    )
    written["structure"] = structure_path

    rows_path = safe_output_path(output_dir, FILENAMES["rows_csv"])
    atomic_write_text(rows_path, rows_csv)
    written["rows_csv"] = rows_path

    formulas_path = safe_output_path(output_dir, FILENAMES["formulas_csv"])
    atomic_write_text(formulas_path, formulas_csv)
    written["formulas_csv"] = formulas_path

    risk_path = safe_output_path(output_dir, FILENAMES["risk_report"])
    atomic_write_text(risk_path, risk_report_md)
    written["risk_report"] = risk_path

    return written
