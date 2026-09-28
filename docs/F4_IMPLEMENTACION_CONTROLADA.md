# Fase 4 – Implementación controlada

## Estado

Esta rama implementa el núcleo seguro de F4 en modo **DRY-RUN / STAGING-FIRST**.
No autoriza escrituras en producción.

## Componentes

- `f4/config.py`: modos, gates, corte financiero y referencia de producción.
- `f4/contracts.py`: contratos `JobContext`, `JobResult` y evento de auditoría.
- `f4/jobs.py`: catálogo J01–J10 y reglas duras.
- `f4/runner.py`: simulador/runner con bloqueo técnico de `MODE=apply`.
- `tests/test_f4_controls.py`: pruebas de catálogo, gates y contrato de conteos.

## Regla de producción

`MODE=apply` se rechaza mientras no estén simultáneamente en PASS:

1. L4 Finanzas.
2. L7 Release.
3. rollback real probado.
4. aprobación de Dirección.

## Estado esperado hoy

- J01–J06: habilitados para dry-run/staging según fuentes validadas.
- J07: `NO_ASIGNABLE` mientras no exista evidencia de ítem/OC para costo real.
- J08: BI no financiero habilitado; margen real/caja permanecen N/D.
- J09: `BLOCKED_EXPECTED_L4`.
- J10: bloqueado por L4/L7.

## Siguiente incremento técnico

1. Adaptadores de lectura de Google Drive/Sheets configurados por `SOURCE_ID`.
2. Persistencia de `AUDIT_LOG` y cuarentena en sandbox.
3. Idempotencia real por `RUN_ID` + claves técnicas.
4. Ejecución de tests T01–T13 en CI/local.
5. Prueba de rollback sobre sandbox antes de cualquier conexión write-capable al ERP.

## Prohibiciones

- No hardcodear secretos.
- No inferir RUC, pagos/cobranzas, costo real ni resultado comercial.
- No mutar numeración legal/fiscal.
- No promover CANDIDATA a CONFIRMADA sin evidencia/aprobación.
- No archivar `ADMINISTRACION 2026` antes de L7 GO.
