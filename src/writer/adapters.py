"""Adaptadores de destino para el writer productivo.

``NullProductionAdapter`` es el default absoluto: no existe integración con el
ERP productivo (``writer_present=false`` para producción real). Cualquier intento
de usarlo falla cerrado con ``WriterAdapterNotConfigured``.

``SandboxUpsertAdapter`` es un adaptador real pero aislado (JSON local dentro de
``private-data`` o un sandbox de test) que permite probar el motor completo
(apply/rollback/idempotencia/detección de modificación concurrente) sin tocar
ningún sistema externo.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Mapping, Protocol


class WriterAdapterNotConfigured(RuntimeError):
    """No existe adaptador productivo real. Ver AGENTS.md: ningún agente escribe en producción."""


class WriterTransientError(RuntimeError):
    """Error recuperable; el motor puede reintentar."""


class WriterPermanentError(RuntimeError):
    """Error no recuperable; el motor no debe reintentar."""


class ProductionAdapter(Protocol):
    def read(self, target: str, key: Mapping[str, str]) -> Mapping[str, object] | None: ...

    def apply(
        self, target: str, key: Mapping[str, str], payload: Mapping[str, object]
    ) -> Mapping[str, object]: ...

    def restore(
        self, target: str, key: Mapping[str, str], before_state: Mapping[str, object] | None
    ) -> None: ...


class NullProductionAdapter:
    """Adaptador productivo inexistente. Bloquea toda operación real."""

    def read(self, target: str, key: Mapping[str, str]) -> Mapping[str, object] | None:
        raise WriterAdapterNotConfigured(
            "No hay adaptador productivo configurado para el ERP real."
        )

    def apply(
        self, target: str, key: Mapping[str, str], payload: Mapping[str, object]
    ) -> Mapping[str, object]:
        raise WriterAdapterNotConfigured(
            "No hay adaptador productivo configurado para el ERP real."
        )

    def restore(
        self, target: str, key: Mapping[str, str], before_state: Mapping[str, object] | None
    ) -> None:
        raise WriterAdapterNotConfigured(
            "No hay adaptador productivo configurado para el ERP real."
        )


def _record_key(target: str, key: Mapping[str, str]) -> str:
    ordered = sorted(key.items())
    return target + "|" + "|".join(f"{k}={v}" for k, v in ordered)


class SandboxUpsertAdapter:
    """Adaptador UPSERT aislado sobre un único archivo JSON local.

    Nunca borra registros de forma automática (UPSERT explícito, ver Fase C).
    """

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._state_path = self.root / "sandbox_state.json"
        if not self._state_path.is_file():
            self._write_state({})

    def _read_state(self) -> dict[str, dict[str, object]]:
        if not self._state_path.is_file():
            return {}
        return json.loads(self._state_path.read_text(encoding="utf-8"))

    def _write_state(self, state: Mapping[str, Mapping[str, object]]) -> None:
        text = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self._state_path.name}.", suffix=".tmp", dir=str(self.root)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self._state_path)
        except Exception:
            try:
                os.remove(tmp_name)
            except OSError:
                pass
            raise

    def read(self, target: str, key: Mapping[str, str]) -> Mapping[str, object] | None:
        return self._read_state().get(_record_key(target, key))

    def apply(
        self, target: str, key: Mapping[str, str], payload: Mapping[str, object]
    ) -> Mapping[str, object]:
        state = self._read_state()
        current = state.get(_record_key(target, key), {})
        merged = {**current, **dict(payload)}
        state[_record_key(target, key)] = merged
        self._write_state(state)
        return merged

    def restore(
        self, target: str, key: Mapping[str, str], before_state: Mapping[str, object] | None
    ) -> None:
        state = self._read_state()
        record_key = _record_key(target, key)
        if before_state is None:
            state.pop(record_key, None)
        else:
            state[record_key] = dict(before_state)
        self._write_state(state)
