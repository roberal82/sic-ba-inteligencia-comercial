# SIC-BA — Estado final técnico (Sprint 006)

## Resumen

```
TECHNICAL = COMPLETE
PRODUCTION = WAITING_FOR_EXTERNAL_EVIDENCE
```

Rama de staging:

`feature/f4-orchestration-dryrun`

Merge técnico Sprint 006:

`645625152151fe03d98267ddd48df0d11c30c82c`

## Estado verificado

| Componente | Estado |
|---|---|
| ERP Drift Engine | READY |
| Staging / quarantine / audit | READY |
| Writer engine | READY / DISABLED |
| Rollback | TESTED / CAS_HARDENED |
| Release Gate | FORMAL L4/L7, FAIL-CLOSED |
| Security | PASS |
| F4 orchestration | PASS |
| F5 cutover simulator | PASS |
| Financial governance | PASS |
| Pipeline governance | PASS |
| Full regression | 269 passed + 4 subtests |
| L4 | FAIL_CLOSED |
| L7 | NO_GO |
| Production adapter | NOT CONFIGURED |
| Producción | LOCKED |
| ADMINISTRACION 2026 | ACTIVE |
| main | UNCHANGED |

## Sprint 006 — endurecimiento de auditoría Hermes

Se cerraron tres riesgos adicionales:

1. **Race de rollback**
   - El rollback ya no depende únicamente de un precheck seguido de restore.
   - El adaptador expone `compare_and_swap_restore`.
   - Si el registro cambia entre precheck y restore, el CAS rechaza la restauración y se conserva el cambio externo.

2. **APPLY interrumpido**
   - Se persiste `APPLY_IN_PROGRESS` antes de invocar el adaptador.
   - Si el proceso cae y no existe resultado final, reutilizar el mismo `run_id` no repite la escritura.
   - El run pasa a `REQUIRES_HUMAN_REVIEW`.

3. **L4/L7 autocertificados**
   - El release gate ignora los flags heredados `l4_pass` y `l7_go`.
   - L4 se deriva de `FinancialGateEvidence` mediante `evaluate_l4`.
   - L7 se deriva de `L7Inputs` mediante `evaluate_l7`, recibiendo el resultado formal de L4.

## CI

Después del merge de Sprint 006, los siete workflows cerraron en SUCCESS:

- SIC-BA release candidate
- Production readiness tests
- Security check
- F4 orchestration tests
- F5 cutover simulation tests
- Financial governance tests
- Pipeline governance tests

Regresión:

```
269 passed, 4 subtests passed, 0 fail
```

Release gate actual:

```
technical_status = RC_READY
production_status = BLOCKED_L4
l4_status = FAIL_CLOSED
l7_status = NO_GO
production_ready = false
```

## Bloqueo actual

No es un defecto de código.

Falta evidencia financiera oficial y homogénea al corte
`2026-09-26T23:59:00-03:00`:

- CxC;
- CxP;
- cheques;
- movimientos bancarios;
- conciliación nominal.

Sin esa evidencia, el comportamiento correcto es:

`L4 = FAIL_CLOSED -> L7 = NO_GO -> PRODUCTION = LOCKED`

## Próximo hito

Construir el paquete privado de evidencia L4 con fuentes reales, hashes y
aprobación identificada. No se debe implementar un adaptador ERP productivo
real hasta que exista evidencia suficiente para probarlo de forma controlada
y reversible.

Ver `docs/CONTINUATION_CHECKPOINT.md`.
