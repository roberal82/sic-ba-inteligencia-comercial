"""Logging estructurado (Fase H).

Cada run productivo, de writer, de gate o de cutover puede registrar una
``RunLogEntry`` aquí. Los eventos se anexan como JSONL, nunca se reescriben.
No se admite ningún campo cuyo nombre sugiera un secreto (password, token,
api_key, credential, secret) — el logger falla cerrado antes de escribir.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


class RunLogState(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    ROLLED_BACK = "ROLLED_BACK"
    PARTIAL = "PARTIAL"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"


class SecretLikeFieldError(ValueError):
    """Se intentó registrar un campo cuyo nombre sugiere un secreto."""


_SECRET_NAME_RE = re.compile(r"(password|secret|token|api[_-]?key|credential)", re.IGNORECASE)


@dataclass(frozen=True)
class RunLogEntry:
    run_id: str
    environment: str
    actor: str
    commit_sha: str
    operation: str
    gate: str
    result: RunLogState
    duration_s: float
    source_hashes: Mapping[str, str] = field(default_factory=dict)
    error: str = ""
    rollback_status: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            object.__setattr__(self, "timestamp", datetime.now(timezone.utc).isoformat())
        for name in ("run_id", "environment", "actor", "commit_sha", "operation", "gate"):
            value = getattr(self, name)
            if _SECRET_NAME_RE.search(value or ""):
                raise SecretLikeFieldError(f"Valor de {name!r} parece contener un secreto.")
        for key in self.source_hashes:
            if _SECRET_NAME_RE.search(key):
                raise SecretLikeFieldError(f"Clave de source_hashes {key!r} parece un secreto.")

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "environment": self.environment,
            "actor": self.actor,
            "commit_sha": self.commit_sha,
            "source_hashes": dict(self.source_hashes),
            "operation": self.operation,
            "gate": self.gate,
            "result": self.result.value,
            "duration_s": self.duration_s,
            "error": self.error,
            "rollback_status": self.rollback_status,
        }


class RunLogger:
    """Escritor JSONL append-only. Nunca sobreescribe eventos previos."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, entry: RunLogEntry) -> None:
        line = json.dumps(entry.as_dict(), ensure_ascii=False, sort_keys=True)
        existing = self.path.read_text(encoding="utf-8") if self.path.is_file() else ""
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=str(self.path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(existing + line + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.path)
        except Exception:
            try:
                os.remove(tmp_name)
            except OSError:
                pass
            raise

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
