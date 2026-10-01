from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SourceAdapterError(RuntimeError):
    """Error controlado al leer una fuente local read-only."""


@dataclass(frozen=True)
class CsvSourceSpec:
    name: str
    path: str
    required_columns: tuple[str, ...] = ()
    key_fields: tuple[str, ...] = ()
    sets_input: str | None = None
    required: bool = True

    @classmethod
    def from_mapping(cls, name: str, raw: dict[str, Any]) -> "CsvSourceSpec":
        if not isinstance(raw, dict):
            raise SourceAdapterError(f"sources.{name} debe ser un objeto JSON.")
        path = str(raw.get("path", "")).strip()
        if not path:
            raise SourceAdapterError(f"sources.{name}.path es obligatorio.")

        def _tuple_of_strings(key: str) -> tuple[str, ...]:
            value = raw.get(key, []) or []
            if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
                raise SourceAdapterError(f"sources.{name}.{key} debe ser una lista de strings no vacíos.")
            return tuple(v.strip() for v in value)

        sets_input = raw.get("sets_input")
        if sets_input is not None:
            if not isinstance(sets_input, str) or not sets_input.strip():
                raise SourceAdapterError(f"sources.{name}.sets_input debe ser string o null.")
            sets_input = sets_input.strip()

        return cls(
            name=name,
            path=path,
            required_columns=_tuple_of_strings("required_columns"),
            key_fields=_tuple_of_strings("key_fields"),
            sets_input=sets_input,
            required=bool(raw.get("required", True)),
        )


@dataclass(frozen=True)
class CsvSnapshot:
    name: str
    source_path: Path
    sha256: str
    headers: tuple[str, ...]
    rows: tuple[dict[str, str], ...]

    @property
    def row_count(self) -> int:
        return len(self.rows)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _confined_path(root: Path, relative_path: str) -> Path:
    root_resolved = root.resolve()
    candidate = (root_resolved / relative_path).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise SourceAdapterError("La fuente intenta escapar de source_root.") from exc
    return candidate


def read_csv_snapshot(source_root: Path, spec: CsvSourceSpec) -> CsvSnapshot | None:
    """Lee una fuente CSV sin modificarla y verifica hash antes/después.

    Las rutas del manifest son relativas a ``source_root``. No se siguen rutas
    fuera de ese árbol, aun cuando contengan ``..`` o symlinks que escapen.
    """

    path = _confined_path(source_root, spec.path)
    if not path.is_file():
        if spec.required:
            raise SourceAdapterError(f"Fuente requerida inexistente: {spec.name}")
        return None

    before = _sha256(path)
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise SourceAdapterError(f"Fuente sin encabezados: {spec.name}")
            headers = tuple(str(h).strip() for h in reader.fieldnames)
            if any(not h for h in headers):
                raise SourceAdapterError(f"Fuente con encabezado vacío: {spec.name}")
            if len(set(headers)) != len(headers):
                raise SourceAdapterError(f"Fuente con encabezados duplicados: {spec.name}")

            missing = [column for column in spec.required_columns if column not in headers]
            if missing:
                raise SourceAdapterError(
                    f"Fuente {spec.name} carece de columnas requeridas: {', '.join(missing)}"
                )

            rows: list[dict[str, str]] = []
            for raw in reader:
                normalized = {
                    header: "" if raw.get(header) is None else str(raw.get(header, ""))
                    for header in headers
                }
                rows.append(normalized)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise SourceAdapterError(f"No se pudo leer la fuente {spec.name}.") from exc

    after = _sha256(path)
    if before != after:
        raise SourceAdapterError(
            f"La fuente {spec.name} cambió durante la lectura; ejecución abortada."
        )

    return CsvSnapshot(
        name=spec.name,
        source_path=path,
        sha256=before,
        headers=headers,
        rows=tuple(rows),
    )
