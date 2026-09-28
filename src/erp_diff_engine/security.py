"""Utilidades de seguridad: hashing, validación de rutas y escritura atómica.

Reglas duras de este módulo:
- Los archivos de entrada (BASE/CURRENT) se abren siempre en modo lectura.
- Ninguna escritura ocurre fuera del directorio de salida (`output_dir`) resuelto.
- Toda escritura de reporte pasa por `atomic_write_*`, nunca por escritura directa.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path


class EngineSecurityError(Exception):
    """Violación de una regla de seguridad (path traversal, ruta inválida, etc.)."""


class EngineInputError(Exception):
    """Entrada inválida o no legible (ruta inexistente, workbook corrupto, etc.)."""


def resolve_strict(path: Path) -> Path:
    """Resuelve una ruta sin seguir un patrón de traversal implícito.

    No prohíbe ``..`` por sí solo (rutas relativas legítimas pueden usarlo),
    pero normaliza para que las comparaciones posteriores sean fiables.
    """

    try:
        return Path(path).expanduser().resolve(strict=False)
    except OSError as exc:  # rutas malformadas en algunos sistemas de archivos
        raise EngineSecurityError(f"Ruta inválida: {path!r} ({exc}).") from exc


def require_existing_file(path: Path, label: str) -> Path:
    resolved = resolve_strict(path)
    if not resolved.exists():
        raise EngineInputError(f"{label} no existe: {resolved}")
    if not resolved.is_file():
        raise EngineInputError(f"{label} no es un archivo regular: {resolved}")
    return resolved


def prepare_output_dir(path: Path, *forbidden_ancestors_of: Path) -> Path:
    """Resuelve y crea (si falta) el directorio de salida.

    Rechaza el caso en que el directorio de salida sea ancestro o descendiente
    de cualquiera de las rutas de entrada, para evitar que un reporte pise un
    insumo o que un insumo termine "dentro" del árbol de salida por error de
    configuración.
    """

    resolved = resolve_strict(path)
    resolved.mkdir(parents=True, exist_ok=True)
    resolved = resolved.resolve(strict=True)

    for other in forbidden_ancestors_of:
        other_resolved = resolve_strict(other)
        if resolved == other_resolved:
            raise EngineSecurityError(
                f"El directorio de salida coincide con una entrada: {resolved}"
            )
        if _is_ancestor(resolved, other_resolved) or _is_ancestor(other_resolved, resolved):
            raise EngineSecurityError(
                "El directorio de salida no puede ser ancestro ni descendiente "
                f"de una ruta de entrada ({resolved} vs {other_resolved})."
            )
    return resolved


def _is_ancestor(candidate_ancestor: Path, candidate_descendant: Path) -> bool:
    try:
        candidate_descendant.relative_to(candidate_ancestor)
        return candidate_ancestor != candidate_descendant
    except ValueError:
        return False


def safe_output_path(output_dir: Path, filename: str) -> Path:
    """Construye una ruta de salida y garantiza que quede dentro de ``output_dir``."""

    if os.path.isabs(filename) or ".." in Path(filename).parts:
        raise EngineSecurityError(f"Nombre de archivo de salida no permitido: {filename!r}")
    candidate = (output_dir / filename).resolve(strict=False)
    if not _is_ancestor(output_dir, candidate) and candidate != output_dir:
        raise EngineSecurityError(
            f"Escritura fuera de output_dir bloqueada: {candidate}"
        )
    return candidate


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    _atomic_write(path, content.encode(encoding))


def atomic_write_bytes(path: Path, content: bytes) -> None:
    _atomic_write(path, content)


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.remove(tmp_name)
        except OSError:
            pass
        raise
