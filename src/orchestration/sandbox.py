from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any


RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


class SandboxError(RuntimeError):
    pass


class SandboxManifestConflict(SandboxError):
    pass


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def manifest_sha256(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def validate_run_id(run_id: str) -> str:
    if not RUN_ID_RE.fullmatch(run_id):
        raise ValueError(
            "run_id inválido: use 1-80 caracteres alfanuméricos, punto, guion o guion bajo."
        )
    return run_id


class SandboxRunStore:
    """Persistencia local aislada por run_id para stage/dry-run.

    No conoce ERP, Drive ni base productiva. Cada ejecución queda encapsulada
    en un directorio bajo `root`. Repetir el mismo run_id con el mismo manifest
    es idempotente; usar el mismo run_id con otro manifest produce conflicto.
    """

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def run_dir(self, run_id: str) -> Path:
        validated = validate_run_id(run_id)
        candidate = (self.root / validated).resolve()
        if self.root != candidate.parent:
            raise SandboxError("run_id intenta escapar del sandbox.")
        return candidate

    def begin(self, run_id: str, manifest: dict[str, Any]) -> tuple[Path, bool]:
        directory = self.run_dir(run_id)
        digest = manifest_sha256(manifest)
        metadata_path = directory / "run_meta.json"

        if directory.exists():
            if not metadata_path.is_file():
                raise SandboxManifestConflict(
                    f"El run_id {run_id} ya existe sin metadata válida."
                )
            current = json.loads(metadata_path.read_text(encoding="utf-8"))
            if current.get("manifest_sha256") != digest:
                raise SandboxManifestConflict(
                    f"El run_id {run_id} ya existe con un manifest diferente."
                )
            return directory, False

        directory.mkdir(parents=False, exist_ok=False)
        self._atomic_json(
            metadata_path,
            {
                "run_id": run_id,
                "manifest_sha256": digest,
                "status": "STARTED",
            },
        )
        self._atomic_json(directory / "manifest.json", manifest)
        return directory, True

    def write_result(self, run_id: str, result: dict[str, Any]) -> Path:
        directory = self.run_dir(run_id)
        if not directory.is_dir():
            raise SandboxError(f"Run inexistente: {run_id}")
        path = directory / "result.json"
        self._atomic_json(path, result)
        return path

    def mark_completed(self, run_id: str, overall: str) -> Path:
        directory = self.run_dir(run_id)
        meta_path = directory / "run_meta.json"
        if not meta_path.is_file():
            raise SandboxError(f"Metadata inexistente: {run_id}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["status"] = "COMPLETED"
        meta["overall"] = overall
        self._atomic_json(meta_path, meta)
        return meta_path

    def rollback(self, run_id: str) -> bool:
        """Elimina únicamente el directorio de ese run_id.

        Devuelve True si existía y fue retirado; False si ya estaba ausente.
        """
        directory = self.run_dir(run_id)
        if not directory.exists():
            return False
        shutil.rmtree(directory)
        return True

    @staticmethod
    def _atomic_json(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
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
