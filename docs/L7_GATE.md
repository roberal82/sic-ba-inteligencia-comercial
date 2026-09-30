# SIC-BA — Gate L7 (decisión GO/NO-GO de producción)

## Propósito

L7 es la decisión final antes de cualquier `execute_go_live()` del motor de
cutover. Implementado en `src/gates/l7_decision.py`.

## Regla dura

L7 **nunca** puede llegar a `GO` sin que los siete elementos sean verdaderos
simultáneamente. No existe un atajo de un solo flag.

## `L7Inputs` — campos evaluados

| Campo | Significado |
|---|---|
| `l4_pass` | Resultado de `evaluate_l4()` (no un booleano suelto declarado aparte) |
| `integrity_pass` | Verificación de integridad de datos/checksum |
| `rollback_pass` | Rollback real probado exitosamente (ver `docs/ROLLBACK_RUNBOOK.md`) |
| `smoke_pass` | Smoke test end-to-end aprobado |
| `uat_pass` | UAT aceptado |
| `manifest_complete` | Manifest de operación completo (writer/cutover) |
| `human_approval` | Aprobación humana explícita |
| `approved_by` / `approval_timestamp` | Obligatorios si `human_approval=True` |

## Uso

```python
from src.gates.l7_decision import L7Inputs, evaluate_l7

decision = evaluate_l7(L7Inputs(
    l4_pass=l4_result.l4_pass,
    integrity_pass=...,
    rollback_pass=...,
    smoke_pass=...,
    uat_pass=...,
    manifest_complete=...,
    human_approval=True,
    approved_by="DIRECCION",
    approval_timestamp="2026-XX-XXT..:..:..-03:00",
))

decision.result  # "GO" | "NO_GO"
decision.l7_go   # bool
decision.reasons # tuple[str, ...]
```

## Integración con el cutover engine

`src.cutover.engine.build_context_from_gates(l4_result, l7_decision, ...)`
construye el `CutoverContext` del simulador F5 a partir de estos objetos, no
de booleanos sueltos pasados a mano — así una integración nueva no puede
"olvidar" pasar por los gates reales.
