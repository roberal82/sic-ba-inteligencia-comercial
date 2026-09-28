"""Modelos de datos del ERP_DIFF_ENGINE.

Todo el módulo trabaja exclusivamente con estructuras en memoria (snapshots,
diferencias, clasificaciones). No conoce rutas privadas ni credenciales.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Classification(str, Enum):
    """Estados de riesgo permitidos por AGENTS.md / SPRINT_001_ERP_DRIFT.md."""

    EXPECTED = "EXPECTED"
    UNDOCUMENTED = "UNDOCUMENTED"
    RISK = "RISK"
    CRITICAL = "CRITICAL"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"


# Orden de severidad para ordenar reportes (mayor índice = más severo).
CLASSIFICATION_SEVERITY: dict[Classification, int] = {
    Classification.EXPECTED: 0,
    Classification.UNDOCUMENTED: 1,
    Classification.REQUIRES_HUMAN_REVIEW: 2,
    Classification.RISK: 3,
    Classification.CRITICAL: 4,
}


class DiffKind(str, Enum):
    SHEET_ADDED = "SHEET_ADDED"
    SHEET_REMOVED = "SHEET_REMOVED"
    SHEET_ORDER_CHANGED = "SHEET_ORDER_CHANGED"
    COLUMN_ADDED = "COLUMN_ADDED"
    COLUMN_REMOVED = "COLUMN_REMOVED"
    HEADER_CHANGED = "HEADER_CHANGED"
    ROW_ADDED = "ROW_ADDED"
    ROW_REMOVED = "ROW_REMOVED"
    VALUE_MODIFIED = "VALUE_MODIFIED"
    TYPE_CHANGED = "TYPE_CHANGED"
    FORMULA_CHANGED = "FORMULA_CHANGED"
    FORMULA_CHANGED_SAME_VALUE = "FORMULA_CHANGED_SAME_VALUE"
    DUPLICATE_KEY = "DUPLICATE_KEY"
    NULL_IN_KEY = "NULL_IN_KEY"
    CONTROL_TOTAL_MISMATCH = "CONTROL_TOTAL_MISMATCH"


@dataclass(frozen=True)
class RowRecord:
    """Una fila de datos (no encabezado) de una hoja."""

    row_number: int  # número de fila real en la planilla (base 1, incluye encabezado)
    values: dict[int, Any] = field(default_factory=dict)  # col_index(0-based) -> valor
    formulas: dict[int, str] = field(default_factory=dict)  # col_index(0-based) -> fórmula


@dataclass(frozen=True)
class SheetSnapshot:
    name: str
    index: int  # posición 0-based en el workbook
    headers: list[Any] = field(default_factory=list)
    rows: list[RowRecord] = field(default_factory=list)

    @property
    def n_cols(self) -> int:
        return len(self.headers)

    @property
    def n_rows(self) -> int:
        return len(self.rows)

    def header_at(self, col_index: int) -> Any:
        if 0 <= col_index < len(self.headers):
            return self.headers[col_index]
        return None

    def column_index(self, header_name: str) -> int | None:
        for idx, header in enumerate(self.headers):
            if header is not None and str(header).strip() == header_name:
                return idx
        return None


@dataclass(frozen=True)
class WorkbookSnapshot:
    path: Path
    sha256: str
    sheet_names: list[str] = field(default_factory=list)
    sheets: dict[str, SheetSnapshot] = field(default_factory=dict)


@dataclass(frozen=True)
class Difference:
    """Una diferencia estructural o de contenido detectada entre BASE y CURRENT."""

    kind: DiffKind
    sheet: str | None
    location: str
    column: str | None = None
    row_key: str | None = None
    base_value: Any = None
    current_value: Any = None
    detail: str = ""


@dataclass(frozen=True)
class ClassifiedDifference:
    difference: Difference
    classification: Classification
    rule_applied: str


@dataclass(frozen=True)
class ExpectedRule:
    """Regla explícita de configuración para marcar una diferencia como EXPECTED.

    Nunca se genera automáticamente: solo existe si el usuario la declaró en el
    archivo de configuración. Ver AGENTS.md: "Nunca EXPECTED por inferencia automática".
    """

    kind: DiffKind
    sheet: str | None = None
    column: str | None = None
    row_key: str | None = None
    note: str = ""

    def matches(self, diff: Difference) -> bool:
        if self.kind != diff.kind:
            return False
        if self.sheet is not None and self.sheet != diff.sheet:
            return False
        if self.column is not None and self.column != diff.column:
            return False
        if self.row_key is not None and self.row_key != diff.row_key:
            return False
        return True


@dataclass(frozen=True)
class EngineConfig:
    base_path: Path
    current_path: Path
    output_dir: Path
    primary_keys: dict[str, list[str]] = field(default_factory=dict)
    control_totals: dict[str, list[str]] = field(default_factory=dict)
    sensitive_columns: dict[str, list[str]] = field(default_factory=dict)
    expected_rules: tuple[ExpectedRule, ...] = field(default_factory=tuple)
    severity_overrides: dict[DiffKind, Classification] = field(default_factory=dict)
    log_file: Path | None = None
