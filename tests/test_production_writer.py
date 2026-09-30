import tempfile
import unittest
from pathlib import Path

from src.writer.adapters import (
    NullProductionAdapter,
    SandboxUpsertAdapter,
    WriterTransientError,
)
from src.writer.engine import ProductionWriter, WriterTimeoutError, WriterValidationError
from src.writer.models import OperationSpec, RunStatus, WriteMode, WriterInterlock
from src.writer.rollback import rollback_run
from src.writer.store import WriterRunConflict


def _full_interlock(**overrides) -> WriterInterlock:
    base = dict(
        l4_pass=True,
        l7_go=True,
        rollback_real_proven=True,
        human_approval=True,
        cutover_window_authorized=True,
        snapshot_ready=True,
        production_write_env="ENABLED",
    )
    base.update(overrides)
    return WriterInterlock(**base)


def _op(op_id="op-1", target="clientes", key=None, payload=None) -> OperationSpec:
    return OperationSpec(
        op_id=op_id,
        target=target,
        key=key or {"id": "C1"},
        payload=payload or {"nombre": "Cliente Uno"},
    )


class WriterInterlockDefaultTests(unittest.TestCase):
    def test_interlock_defaults_to_fully_disabled(self):
        interlock = WriterInterlock()
        self.assertFalse(interlock.apply_authorized)
        self.assertEqual(len(interlock.blocking_reasons), 7)

    def test_env_var_alone_is_not_enough(self):
        interlock = WriterInterlock(production_write_env="ENABLED")
        self.assertFalse(interlock.apply_authorized)
        self.assertIn("L4 no está en PASS", interlock.blocking_reasons)

    def test_from_env_reads_explicit_mapping_not_ambient_state(self):
        interlock = WriterInterlock.from_env(
            l4_pass=True,
            l7_go=True,
            rollback_real_proven=True,
            human_approval=True,
            cutover_window_authorized=True,
            snapshot_ready=True,
            environ={"SIC_BA_PRODUCTION_WRITE": "ENABLED"},
        )
        self.assertTrue(interlock.apply_authorized)


class WriterDryRunAndStageTests(unittest.TestCase):
    def test_dry_run_never_touches_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = ProductionWriter(Path(tmp), NullProductionAdapter(), WriterInterlock())
            result = writer.execute("run-dry-1", [_op()], WriteMode.DRY_RUN)
            self.assertEqual(result.status, RunStatus.SIMULATED.value)
            self.assertEqual(result.operations[0].after_state, None)

    def test_stage_persists_manifest_without_calling_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = ProductionWriter(Path(tmp), NullProductionAdapter(), WriterInterlock())
            result = writer.execute("run-stage-1", [_op()], WriteMode.STAGE)
            self.assertEqual(result.status, RunStatus.STAGED.value)

    def test_apply_without_interlock_is_blocked_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = ProductionWriter(Path(tmp), NullProductionAdapter(), WriterInterlock())
            result = writer.execute("run-apply-blocked", [_op()], WriteMode.APPLY)
            self.assertEqual(result.status, RunStatus.BLOCKED.value)
            self.assertTrue(result.reasons)


class WriterBatchAndValidationTests(unittest.TestCase):
    def test_batch_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = ProductionWriter(Path(tmp), NullProductionAdapter(), WriterInterlock(), batch_limit=2)
            ops = [_op(op_id=f"op-{i}") for i in range(3)]
            with self.assertRaises(WriterValidationError):
                writer.execute("run-batch", ops, WriteMode.DRY_RUN)

    def test_duplicate_op_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = ProductionWriter(Path(tmp), NullProductionAdapter(), WriterInterlock())
            with self.assertRaises(WriterValidationError):
                writer.execute("run-dup", [_op(op_id="x"), _op(op_id="x")], WriteMode.DRY_RUN)


class WriterApplyScenarioTests(unittest.TestCase):
    """Cubre los 8 escenarios exigidos en la Fase D del mandato."""

    def _writer(self, tmp: str, adapter=None, **interlock_overrides) -> tuple[ProductionWriter, SandboxUpsertAdapter]:
        adapter = adapter or SandboxUpsertAdapter(Path(tmp) / "sandbox")
        writer = ProductionWriter(
            Path(tmp) / "store",
            adapter,
            _full_interlock(**interlock_overrides),
            sleep_fn=lambda _seconds: None,
        )
        return writer, adapter

    def test_1_apply_exitoso(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer, adapter = self._writer(tmp)
            result = writer.execute("run-ok", [_op("op-1"), _op("op-2", key={"id": "C2"})], WriteMode.APPLY)
            self.assertEqual(result.status, RunStatus.SUCCESS.value)
            self.assertEqual(len(result.operations), 2)
            self.assertEqual(adapter.read("clientes", {"id": "C1"})["nombre"], "Cliente Uno")

    def test_2_apply_parcial_por_excepcion_entre_operaciones(self):
        class FlakyAdapter(SandboxUpsertAdapter):
            def apply(self, target, key, payload):
                if key.get("id") == "C2":
                    raise RuntimeError("fallo permanente simulado")
                return super().apply(target, key, payload)

        with tempfile.TemporaryDirectory() as tmp:
            adapter = FlakyAdapter(Path(tmp) / "sandbox")
            writer, _ = self._writer(tmp, adapter=adapter)
            result = writer.execute(
                "run-partial",
                [_op("op-1"), _op("op-2", key={"id": "C2"}), _op("op-3", key={"id": "C3"})],
                WriteMode.APPLY,
            )
            self.assertEqual(result.status, RunStatus.PARTIAL.value)
            self.assertEqual(len(result.operations), 1)
            self.assertIsNone(adapter.read("clientes", {"id": "C3"}))

    def test_3_excepcion_entre_operaciones_no_corrompe_estado_previo(self):
        class FailSecond(SandboxUpsertAdapter):
            calls = 0

            def apply(self, target, key, payload):
                type(self).calls += 1
                if type(self).calls == 2:
                    raise RuntimeError("boom")
                return super().apply(target, key, payload)

        with tempfile.TemporaryDirectory() as tmp:
            adapter = FailSecond(Path(tmp) / "sandbox")
            writer, _ = self._writer(tmp, adapter=adapter)
            result = writer.execute("run-mid-fail", [_op("op-1"), _op("op-2", key={"id": "C2"})], WriteMode.APPLY)
            self.assertEqual(result.status, RunStatus.PARTIAL.value)
            self.assertEqual(adapter.read("clientes", {"id": "C1"})["nombre"], "Cliente Uno")

    def test_4_rollback_total_restaura_estado_previo(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = SandboxUpsertAdapter(Path(tmp) / "sandbox")
            adapter.apply("clientes", {"id": "C1"}, {"nombre": "Original"})
            writer = ProductionWriter(
                Path(tmp) / "store", adapter, _full_interlock(), sleep_fn=lambda _s: None
            )
            writer.execute("run-rb", [_op("op-1", payload={"nombre": "Nuevo"})], WriteMode.APPLY)
            self.assertEqual(adapter.read("clientes", {"id": "C1"})["nombre"], "Nuevo")

            result = rollback_run(Path(tmp) / "store", "run-rb", adapter)
            self.assertEqual(result.status, RunStatus.ROLLED_BACK.value)
            self.assertEqual(adapter.read("clientes", {"id": "C1"})["nombre"], "Original")

    def test_5_rollback_idempotente(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer, adapter = self._writer(tmp)
            writer.execute("run-rb2", [_op()], WriteMode.APPLY)
            first = rollback_run(Path(tmp) / "store", "run-rb2", adapter)
            second = rollback_run(Path(tmp) / "store", "run-rb2", adapter)
            self.assertEqual(first.status, RunStatus.ROLLED_BACK.value)
            self.assertEqual(second.status, RunStatus.ROLLED_BACK.value)

    def test_6_retry_despues_de_rollback_con_nuevo_run_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer, adapter = self._writer(tmp)
            writer.execute("run-a", [_op(payload={"nombre": "V1"})], WriteMode.APPLY)
            rollback_run(Path(tmp) / "store", "run-a", adapter)
            retry = writer.execute("run-a-retry", [_op(payload={"nombre": "V2"})], WriteMode.APPLY)
            self.assertEqual(retry.status, RunStatus.SUCCESS.value)
            self.assertEqual(adapter.read("clientes", {"id": "C1"})["nombre"], "V2")

    def test_7_doble_ejecucion_del_mismo_run_id_es_idempotente(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer, adapter = self._writer(tmp)
            ops = [_op()]
            first = writer.execute("run-dup-exec", ops, WriteMode.APPLY)
            second = writer.execute("run-dup-exec", ops, WriteMode.APPLY)
            self.assertEqual(first.status, RunStatus.SUCCESS.value)
            self.assertEqual(second.status, RunStatus.SUCCESS.value)
            # Debe seguir habiendo un único registro upsert, no dos aplicaciones.
            state = adapter._read_state()
            self.assertEqual(len(state), 1)

        # Mismo run_id con operaciones distintas debe fallar cerrado.
        with tempfile.TemporaryDirectory() as tmp:
            writer, _ = self._writer(tmp)
            writer.execute("run-conflict", [_op(payload={"nombre": "A"})], WriteMode.APPLY)
            with self.assertRaises(WriterRunConflict):
                writer.execute("run-conflict", [_op(payload={"nombre": "B"})], WriteMode.APPLY)

    def test_8_modificacion_externa_concurrente_bloquea_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer, adapter = self._writer(tmp)
            writer.execute("run-conc", [_op()], WriteMode.APPLY)
            # Alguien (fuera del writer) modifica el registro después del apply.
            adapter.apply("clientes", {"id": "C1"}, {"nombre": "Modificado externamente"})

            result = rollback_run(Path(tmp) / "store", "run-conc", adapter)
            self.assertEqual(result.status, RunStatus.REQUIRES_HUMAN_REVIEW.value)
            # No se debe haber tocado el registro modificado externamente.
            self.assertEqual(adapter.read("clientes", {"id": "C1"})["nombre"], "Modificado externamente")


class WriterRetryAndTimeoutTests(unittest.TestCase):
    def test_transient_error_is_retried_then_succeeds(self):
        class FlakyOnce(SandboxUpsertAdapter):
            attempts = 0

            def apply(self, target, key, payload):
                type(self).attempts += 1
                if type(self).attempts == 1:
                    raise WriterTransientError("temporal")
                return super().apply(target, key, payload)

        with tempfile.TemporaryDirectory() as tmp:
            adapter = FlakyOnce(Path(tmp) / "sandbox")
            writer = ProductionWriter(
                Path(tmp) / "store", adapter, _full_interlock(), sleep_fn=lambda _s: None
            )
            result = writer.execute("run-retry", [_op()], WriteMode.APPLY)
            self.assertEqual(result.status, RunStatus.SUCCESS.value)
            self.assertEqual(result.operations[0].attempts, 2)

    def test_timeout_marks_operation_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = SandboxUpsertAdapter(Path(tmp) / "sandbox")
            clock_values = iter([0.0, 100.0])
            writer = ProductionWriter(
                Path(tmp) / "store",
                adapter,
                _full_interlock(),
                sleep_fn=lambda _s: None,
                clock=lambda: next(clock_values),
                timeout_s=5.0,
            )
            result = writer.execute("run-timeout", [_op()], WriteMode.APPLY)
            self.assertEqual(result.status, RunStatus.FAILED.value)
            self.assertTrue(any("timeout" in r.lower() for r in result.reasons))


if __name__ == "__main__":
    unittest.main()
