"""Adaptadores de destino para el writer productivo.

El adaptador nulo bloquea toda escritura real. El adaptador sandbox permite
probar apply/rollback/idempotencia sin tocar sistemas externos. El protocolo
incluye compare_and_swap_restore: un rollback nunca debe sobrescribir un estado
que haya cambiado después del apply.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Mapping, Protocol


class WriterAdapterNotConfigured(RuntimeError):
    """No existe adaptador productivo real."""


class WriterTransientError(RuntimeError):
    """Error recuperable y explícitamente seguro de reintentar."""


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

    def compare_and_swap_restore(
        self,
        target: str,
        key: Mapping[str, str],
        expected_state: Mapping[str, object] | None,
        before_state: Mapping[str, object] | None,
    ) -> bool:
        """Restaura solo si el estado actual coincide exactamente con expected_state."""


class NullProductionAdapter:
    """Adaptador productivo inexistente. Bloquea toda operación real."""

    def _blocked(self):
        raise WriterAdapterNotConfigured(
            "No hay adaptador productivo configurado para el ERP real."
        )

    def read(self, target: str, key: Mapping[str, str]) -> Mapping[str, object] | None:
        self._blocked()

    def apply(
        self, target: str, key: Mapping[str, str], payload: Mapping[str, object]
    ) -> Mapping[str, object]:
        self._blocked()

    def restore(
        self, target: str, key: Mapping[str, str], before_state: Mapping[str, object] | None
    ) -> None:
        self._blocked()

    def compare_and_swap_restore(
        self,
        target: str,
        key: Mapping[str, str],
        expected_state: Mapping[str, object] | None,
        before_state: Mapping[str, object] | None,
    ) -> bool:
        self._blocked()


def _record_key(target: str, key: Mapping[str, str]) -> str:
    ordered = sorted(key.items())
    return target + "|" + "|".join(f"{k}={v}" for k, v in ordered)


class SandboxUpsertAdapter:
    """Adaptador UPSERT aislado sobre un archivo JSON local.

    Las operaciones read/apply/restore/CAS están protegidas con un RLock para
    cerrar la carrera entre el precheck y la restauración dentro del proceso.
    Un adaptador productivo real deberá implementar la misma semántica CAS de
    forma atómica en su backend (transacción/version/ETag).
    """

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._state_path = self.root / "sandbox_state.json"
        self._lock = threading.RLock()
        if not self._state_path.is_file():
            self._write_state({})

    def _read_state(self) -> dict[str, dict[str, object]]:
        with self._lock:
            if not self._state_path.is_file():
                return {}
            return json.loads(self._state_path.read_text(encoding="utf-8"))

    def _write_state(self, state: Mapping[str, Mapping[str, object]]) -> None:
        with self._lock:
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
        with self._lock:
            current = self._read_state().get(_record_key(target, key))
            return dict(current) if current is not None else None

    def apply(
        self, target: str, key: Mapping[str, str], payload: Mapping[str, object]
    ) -> Mapping[str, object]:
        with self._lock:
            state = self._read_state()
            record_key = _record_key(target, key)
            current = state.get(record_key, {})
            merged = {**current, **dict(payload)}
            state[record_key] = merged
            self._write_state(state)
            return dict(merged)

    def restore(
        self, target: str, key: Mapping[str, str], before_state: Mapping[str, object] | None
    ) -> None:
        with self._lock:
            state = self._read_state()
            record_key = _record_key(target, key)
            if before_state is None:
                state.pop(record_key, None)
            else:
                state[record_key] = dict(before_state)
            self._write_state(state)

    def compare_and_swap_restore(
        self,
        target: str,
        key: Mapping[str, str],
        expected_state: Mapping[str, object] | None,
        before_state: Mapping[str, object] | None,
    ) -> bool:
        with self._lock:
            state = self._read_state()
            record_key = _record_key(target, key)
            current = state.get(record_key)
            expected = dict(expected_state) if expected_state is not None else None
            if current != expected:
                return False
            if before_state is None:
                state.pop(record_key, None)
            else:
                state[record_key] = dict(before_state)
            self._write_state(state)
            return True
