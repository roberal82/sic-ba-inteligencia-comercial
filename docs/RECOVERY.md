# SIC-BA — Recuperación ante fallos

## Escritura parcial del writer (`RunStatus.PARTIAL`)

Ocurre cuando una operación falla después de que otras ya se aplicaron
exitosamente. El motor detiene el loop inmediatamente (no sigue intentando
las operaciones restantes) y registra:

- Las operaciones completadas con su `before_state`/`after_state`.
- La razón del fallo (`result.reasons`).

**Recuperación:**

1. Ejecutar `rollback_run(store_root, run_id, adapter)` para revertir las
   operaciones que sí se aplicaron (ver `docs/ROLLBACK_RUNBOOK.md`).
2. Diagnosticar la causa del fallo (transitoria vs. permanente).
3. Reintentar con un **nuevo** `run_id` una vez corregida la causa. Reusar el
   mismo `run_id` con las mismas operaciones es idempotente y no vuelve a
   tocar el adaptador; con operaciones distintas, falla cerrado
   (`WriterRunConflict`).

## `RunStatus.BLOCKED` (APPLY sin interlock completo)

No es un fallo del sistema: es el comportamiento default esperado.
`result.reasons` lista exactamente qué falta (`WriterInterlock.blocking_reasons`).
No hay recuperación automática — se resuelve completando los gates reales
(L4, L7, rollback probado, aprobación humana, ventana de cutover, snapshot,
`SIC_BA_PRODUCTION_WRITE=ENABLED`).

## `RunStatus.REQUIRES_HUMAN_REVIEW` (rollback)

Se produce cuando el rollback detecta que el estado actual de una operación
ya no coincide con lo que el writer dejó (`after_fingerprint`), es decir,
algo externo modificó ese registro después del `apply`. El rollback se
detiene por completo — no revierte nada, ni siquiera lo que sí coincide.

**Recuperación (manual, no hay atajo automático):**

1. Comparar el estado actual real contra `before_state`/`after_state`
   guardados en `store_root/<run_id>/operations/*.json`.
2. Decidir si el estado actual (con la modificación externa) es aceptable o
   si requiere corrección manual puntual.
3. Documentar la decisión — esto es evidencia para una futura aprobación L7.

## Timeout de operación (`RunStatus.FAILED` con razón de timeout)

Una operación que excede `timeout_s` se marca como fallo permanente para esa
ejecución (no se reintenta automáticamente un timeout, a diferencia de
`WriterTransientError`). Recuperación: investigar la lentitud del adaptador
real antes de reintentar con un nuevo `run_id`.

## Corrupción de metadata de un run

Si `run_meta.json` existe pero es inválido, `WriterRunStore`/`StageRunStore`
lanzan un error explícito (`WriterRunConflict`/`StageRunConflict`) en lugar de
adivinar el estado. No hay reparación automática de metadata corrupta:
requiere inspección manual del directorio del run.

## Fuera de alcance de este documento

Recuperación de fallos del ERP productivo real: no aplica porque este
repositorio no tiene ningún camino de escritura hacia él
(`NullProductionAdapter`).
