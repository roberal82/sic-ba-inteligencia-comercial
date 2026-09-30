from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

from .models import OperationRecord

SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


class WriterStoreError(RuntimeError):
    pass


class WriterRunConflict(WriterStoreError):
    """El run_id ya existe con un manifest/operaciones distinto (fail-closed)."""


def _validate_name(value: str, label: str) -> str:
    if not SAFE_NAME_RE.fullmatch(value):
        raise WriterStoreError(
            f"{label} inválido: use 1-80 caracteres alfanuméricos, punto, guion o guion bajo."
        )
    return value


class WriterRunStore:
    """Persistencia local de runs del writer productivo.

    Cada ``run_id`` vive en su propio directorio bajo ``root``. Reutilizar un
    ``run_id`` con una huella (fingerprint) distinta falla cerrado; con la misma
    huella, la ejecución es idempotente y no vuelve a tocar el adaptador.
    """

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def run_dir(self, run_id: str) -> Path:
        safe = _validate_name(run_id, "run_id")
        candidate = (self.root / safe).resolve()
        if candidate.parent != self.root:
            raise WriterStoreError("run_id intenta escapar del store root.")
        return candidate

    def begin(self, run_id: str, fingerprint: str, manifest_summary: dict[str, Any]) -> tuple[Path, bool]:
        directory = self.run_dir(run_id)
        meta_path = directory / "run_meta.json"

        if directory.exists():
            if not meta_path.is_file():
                raise WriterRunConflict(f"El run_id {run_id} existe sin metadata válida.")
            current = json.loads(meta_path.read_text(encoding="utf-8"))
            if current.get("fingerprint") != fingerprint:
                raise WriterRunConflict(
                    f"El run_id {run_id} ya existe con operaciones o modo distinto."
                )
            return directory, False

        directory.mkdir(parents=False, exist_ok=False)
        for child in ("operations", "audit"):
            (directory / child).mkdir()

        self._atomic_json(
            meta_path,
            {
                "run_id": run_id,
                "fingerprint": fingerprint,
                "status": "STARTED",
                "manifest_summary": manifest_summary,
            },
        )
        return directory, True

    def read_meta(self, run_id: str) -> dict[str, Any] | None:
        directory = self.run_dir(run_id)
        meta_path = directory / "run_meta.json"
        if not meta_path.is_file():
            return None
        return json.loads(meta_path.read_text(encoding="utf-8"))

    def set_status(self, run_id: str, status: str, **extra: Any) -> None:
        directory = self.run_dir(run_id)
        meta_path = directory / "run_meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["status"] = status
        meta.update(extra)
        self._atomic_json(meta_path, meta)

    def record_operation(self, run_id: str, record: OperationRecord) -> None:
        directory = self.run_dir(run_id)
        safe_op_id = _validate_name(record.op_id, "op_id")
        self._atomic_json(directory / "operations" / f"{safe_op_id}.json", record.as_dict())
        order_path = directory / "operations_order.json"
        order = json.loads(order_path.read_text(encoding="utf-8")) if order_path.is_file() else []
        if record.op_id not in order:
            order.append(record.op_id)
        self._atomic_json(order_path, order)

    def read_operations(self, run_id: str) -> list[OperationRecord]:
        directory = self.run_dir(run_id)
        order_path = directory / "operations_order.json"
        if not order_path.is_file():
            return []
        order = json.loads(order_path.read_text(encoding="utf-8"))
        records = []
        for op_id in order:
            safe_op_id = _validate_name(op_id, "op_id")
            path = directory / "operations" / f"{safe_op_id}.json"
            if path.is_file():
                records.append(OperationRecord.from_dict(json.loads(path.read_text(encoding="utf-8"))))
        return records

    def write_result(self, run_id: str, result: dict[str, Any]) -> None:
        directory = self.run_dir(run_id)
        self._atomic_json(directory / "result.json", result)

    def read_result(self, run_id: str) -> dict[str, Any] | None:
        directory = self.run_dir(run_id)
        path = directory / "result.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def append_audit(self, run_id: str, event: dict[str, Any]) -> None:
        directory = self.run_dir(run_id)
        path = directory / "audit" / "events.jsonl"
        existing = path.read_text(encoding="utf-8") if path.is_file() else ""
        row = dict(event)
        row["sequence"] = existing.count("\n") + 1
        line = json.dumps(row, ensure_ascii=False, sort_keys=True)
        self._atomic_text(path, existing + line + "\n")

    @staticmethod
    def _atomic_json(path: Path, payload: Any) -> None:
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        WriterRunStore._atomic_text(path, text)

    @staticmethod
    def _atomic_text(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            temp_path = Path(handle.name)
        temp_path.replace(path)
