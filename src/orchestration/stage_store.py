from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .adapters import CsvSnapshot


SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


class StageStoreError(RuntimeError):
    pass


class StageRunConflict(StageStoreError):
    pass


@dataclass(frozen=True)
class StageStats:
    domain: str
    source_rows: int
    staged_rows: int
    quarantined_rows: int
    exact_duplicates: int
    source_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "source_rows": self.source_rows,
            "staged_rows": self.staged_rows,
            "quarantined_rows": self.quarantined_rows,
            "exact_duplicates": self.exact_duplicates,
            "source_sha256": self.source_sha256,
        }


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _validate_name(value: str, label: str) -> str:
    if not SAFE_NAME_RE.fullmatch(value):
        raise StageStoreError(
            f"{label} inválido: use 1-80 caracteres alfanuméricos, punto, guion o guion bajo."
        )
    return value


class StageRunStore:
    """Persistencia local aislada para Sprint 002.

    Cada ``run_id`` queda en un directorio propio. La huella de ejecución incluye
    manifest + hashes de fuentes, por lo que reutilizar un run_id con contenido
    distinto falla cerrado. Ninguna operación conoce rutas productivas.
    """

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def run_dir(self, run_id: str) -> Path:
        safe = _validate_name(run_id, "run_id")
        candidate = (self.root / safe).resolve()
        if candidate.parent != self.root:
            raise StageStoreError("run_id intenta escapar del staging root.")
        return candidate

    def begin(self, run_id: str, fingerprint: str, manifest_summary: dict[str, Any]) -> tuple[Path, bool]:
        directory = self.run_dir(run_id)
        meta_path = directory / "run_meta.json"

        if directory.exists():
            if not meta_path.is_file():
                raise StageRunConflict(f"El run_id {run_id} existe sin metadata válida.")
            current = json.loads(meta_path.read_text(encoding="utf-8"))
            if current.get("execution_fingerprint") != fingerprint:
                raise StageRunConflict(
                    f"El run_id {run_id} ya existe con manifest o fuentes diferentes."
                )
            return directory, False

        directory.mkdir(parents=False, exist_ok=False)
        for child in ("staged", "quarantine", "meta", "audit"):
            (directory / child).mkdir()

        self._atomic_json(
            meta_path,
            {
                "run_id": run_id,
                "execution_fingerprint": fingerprint,
                "status": "STARTED",
                "manifest_summary": manifest_summary,
            },
        )
        return directory, True

    def stage_snapshot(
        self,
        run_id: str,
        domain: str,
        snapshot: CsvSnapshot,
        key_fields: Iterable[str],
    ) -> StageStats:
        directory = self.run_dir(run_id)
        if not directory.is_dir():
            raise StageStoreError(f"Run inexistente: {run_id}")

        safe_domain = _validate_name(domain, "domain")
        keys = tuple(key_fields)
        for key in keys:
            if key not in snapshot.headers:
                raise StageStoreError(
                    f"La clave {key} no existe en encabezados de {domain}."
                )

        accepted: list[dict[str, Any]] = []
        quarantine: list[dict[str, Any]] = []
        seen: dict[tuple[str, ...], dict[str, str]] = {}
        exact_duplicates = 0

        for index, row in enumerate(snapshot.rows, start=2):
            if keys:
                key = tuple(row.get(field, "").strip() for field in keys)
                if any(not value for value in key):
                    quarantine.append(
                        {"line": index, "reason": "MISSING_KEY", "key_fields": list(keys)}
                    )
                    continue

                prior = seen.get(key)
                if prior is not None:
                    if prior == row:
                        exact_duplicates += 1
                    else:
                        quarantine.append(
                            {
                                "line": index,
                                "reason": "DUPLICATE_KEY_CONFLICT",
                                "key_fields": list(keys),
                                "key_sha256": hashlib.sha256(
                                    canonical_json(key).encode("utf-8")
                                ).hexdigest(),
                            }
                        )
                    continue
                seen[key] = dict(row)

            accepted.append({"line": index, "row": row})

        self._atomic_jsonl(directory / "staged" / f"{safe_domain}.jsonl", accepted)
        self._atomic_jsonl(directory / "quarantine" / f"{safe_domain}.jsonl", quarantine)

        stats = StageStats(
            domain=safe_domain,
            source_rows=snapshot.row_count,
            staged_rows=len(accepted),
            quarantined_rows=len(quarantine),
            exact_duplicates=exact_duplicates,
            source_sha256=snapshot.sha256,
        )
        self._atomic_json(directory / "meta" / f"{safe_domain}.json", stats.as_dict())
        return stats

    def write_audit(self, run_id: str, events: list[dict[str, Any]]) -> Path:
        directory = self.run_dir(run_id)
        path = directory / "audit" / "events.jsonl"
        sanitized: list[dict[str, Any]] = []
        for sequence, event in enumerate(events, start=1):
            row = dict(event)
            row["sequence"] = sequence
            sanitized.append(row)
        self._atomic_jsonl(path, sanitized)
        return path

    def write_result(self, run_id: str, result: dict[str, Any]) -> Path:
        directory = self.run_dir(run_id)
        path = directory / "result.json"
        self._atomic_json(path, result)
        return path

    def mark_completed(self, run_id: str, overall: str) -> Path:
        directory = self.run_dir(run_id)
        meta_path = directory / "run_meta.json"
        if not meta_path.is_file():
            raise StageStoreError(f"Metadata inexistente: {run_id}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["status"] = "COMPLETED"
        meta["overall"] = overall
        self._atomic_json(meta_path, meta)
        return meta_path

    def rollback(self, run_id: str) -> bool:
        directory = self.run_dir(run_id)
        if not directory.exists():
            return False
        shutil.rmtree(directory)
        return True

    @staticmethod
    def _atomic_json(path: Path, payload: Any) -> None:
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        StageRunStore._atomic_text(path, text)

    @staticmethod
    def _atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
        text = "".join(canonical_json(row) + "\n" for row in rows)
        StageRunStore._atomic_text(path, text)

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
