# SIC-BA — Runbook de rollback real

Cubre `src/writer/rollback.py` (writer productivo, Sprint 005). Para el
rollback de staging de Sprint 002 (datos no financieros), ver
`src/orchestration/operational.rollback_operational_run()` y
`docs/RUNBOOK_STAGING.md`.

## Modelo mental

Cada ejecución del writer (`ProductionWriter.execute(run_id, operations, mode)`)
queda registrada en `WriterRunStore` con, por operación:

- `payload_sha256` — huella de lo que se pidió escribir.
- `before_state` / `before_fingerprint` — estado exacto antes del `apply`.
- `after_state` / `after_fingerprint` — estado exacto después del `apply`.

El rollback usa esos fingerprints para decidir si es seguro restaurar.

## Procedimiento

```python
from src.writer.rollback import rollback_run

result = rollback_run(store_root, run_id, adapter)
result.status  # ROLLED_BACK | REQUIRES_HUMAN_REVIEW
```

1. Si el run ya está `ROLLED_BACK`, la llamada es un no-op idempotente (no
   vuelve a tocar el adaptador).
2. Si el run no tiene operaciones registradas, se marca `ROLLED_BACK`
   directamente (nada que revertir).
3. **Antes de restaurar nada**, se lee el estado actual de cada operación y se
   compara contra `after_fingerprint`. Si **cualquiera** no coincide (alguien
   modificó ese registro después del `apply`), el rollback completo se
   detiene: `status = REQUIRES_HUMAN_REVIEW`, no se restaura absolutamente
   nada, ni siquiera las operaciones que sí coinciden.
4. Si todo coincide, se restauran las operaciones en orden inverso
   (`adapter.restore(target, key, before_state)`), verificando checksum tras
   cada restauración. Un mismatch a mitad de camino también detiene el
   proceso en `REQUIRES_HUMAN_REVIEW` (fail-closed, nunca "rollback parcial
   silencioso").
5. Solo si todo se restauró y verificó, el run pasa a `ROLLED_BACK`.

## Garantías probadas (`tests/test_production_writer.py`)

1. Apply exitoso.
2. Apply parcial: una excepción a mitad de las operaciones dejan `PARTIAL`,
   con solo las operaciones completadas registradas.
3. La operación previa a la excepción no se corrompe.
4. Rollback total restaura el estado previo exacto.
5. Rollback idempotente (llamar dos veces es seguro).
6. Retry después de rollback: un nuevo `run_id` puede reintentar la operación.
7. Doble ejecución del mismo `run_id` con las mismas operaciones es
   idempotente (no se re-aplica); el mismo `run_id` con operaciones distintas
   falla cerrado (`WriterRunConflict`).
8. Modificación externa concurrente detectada antes de rollback: bloquea todo
   el rollback en `REQUIRES_HUMAN_REVIEW`.

## Qué hacer ante `REQUIRES_HUMAN_REVIEW`

No hay acción automática. Un humano debe:

1. Inspeccionar `store_root/<run_id>/operations/*.json` y comparar contra el
   estado actual real del destino.
2. Decidir manualmente si el estado actual es aceptable o si requiere
   corrección manual puntual.
3. Documentar la decisión (esto alimenta `human_approval`/`approved_by` para
   L7 si corresponde).

Nunca "forzar" el rollback sobreescribiendo la verificación de checksum.
