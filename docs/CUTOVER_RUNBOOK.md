# SIC-BA — Runbook de cutover (F5 → motor de cutover)

## Secuencia (10 pasos, `src/cutover/simulator.py`)

1. Snapshot final de fuentes y ERP legacy.
2. Freeze de escritura legacy (requiere ventana autorizada).
3. Carga de maestros/transacciones no financieras.
4. Validación de cardinalidad, claves y relaciones.
5. Carga financiera CxC/CxP/bancos/cheques (bloqueada sin L4 PASS).
6. Smoke test end-to-end (parcial si L4 no está en PASS).
7. Aprobación UAT / aceptación.
8. Go-live ERP productivo (requiere TODO lo anterior + L4 + L7 + rollback real
   probado + aprobación humana).
9. Convivencia controlada (solo si el go-live real ya ocurrió).
10. Archivar ADMINISTRACION 2026 → elegible solo con go-live real estable +
    validación financiera + aprobación humana de archivado. Nunca automático.

## Cómo evaluar el estado actual (sin ejecutar nada)

```powershell
& "C:\BLANCO_ASOCIADOS_AI\.venv\Scripts\python.exe" run_f5.py `
  --manifest config\f5_cutover.example.json --pretty
```

O, con los gates reales L4/L7 en lugar de flags sueltos:

```python
from src.cutover.engine import CutoverEngine, build_context_from_gates

ctx = build_context_from_gates(l4_result, l7_decision, **otros_flags_f5)
engine = CutoverEngine(ctx)
resultado = engine.evaluate()  # nunca muta nada
```

## Ejecución real (`execute_go_live`)

`CutoverEngine.execute_go_live()` **siempre** lanza
`CutoverEngineBlockedError` en este sprint. Esto es intencional: no existe
ningún adaptador productivo real contra el ERP (ver
`src.writer.NullProductionAdapter`). El motor está *preparado* — la secuencia,
los gates y el interlock del writer ya están conectados — para que, el día
que exista un adaptador real y todos los gates estén en GO, el camino a
producción sea corto y no requiera rediseño.

## Puntos de rollback

Cada paso del simulador declara su `rollback_point` (`RP-01`..`RP-04`). Antes
de autorizar cualquier ejecución real de un paso, debe existir rollback
probado hasta ese punto (ver `docs/ROLLBACK_RUNBOOK.md`).

## Legacy (ADMINISTRACION 2026)

No se archiva ni se borra automáticamente en ningún punto de este código. El
campo `legacy_archive_simulated` del resultado del simulador es informativo:
indica si las condiciones formales se cumplen, nunca ejecuta el archivado.
