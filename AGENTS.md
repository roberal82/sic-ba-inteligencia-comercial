# SIC-BA — Reglas de trabajo multiagente

Este repositorio es público. Ningún agente puede versionar datos privados de Blanco & Asociados, credenciales, IDs internos de Drive, extractos bancarios, CxC/CxP, documentos de clientes/proveedores ni copias del ERP.

## Regla central

**Ningún agente escribe en producción.** Todo cambio se desarrolla y valida en branch/worktree, staging, copia o sandbox. El ERP productivo solo puede modificarse con gate técnico PASS, L4/L7 cuando corresponda y aprobación humana explícita.

## Roles

- `agent/claude-drift`: BUILDER. Implementa `ERP_DIFF_ENGINE` y tests funcionales.
- `agent/codex-drift`: QA adversarial. Revisa código, seguridad, idempotencia, falsos positivos/negativos y amplía tests.
- `agent/hermes-drift`: DATA/BATCH. Inventaría y normaliza metadata de copias/snapshots privados; no decide relaciones financieras.
- `agent/gemini-drift`: VALIDATOR. Contrasta resultados y clasifica discrepancias; no modifica fuentes.
- `sprint/001-erp-drift`: rama de integración del Sprint 001.

## Datos privados

Deben vivir fuera del repo, por ejemplo:

`C:\BLANCO_ASOCIADOS_AI\private-data\`

Subdirectorios recomendados:

- `input/`
- `staging/`
- `snapshots/`
- `outputs/`
- `logs/`

Nunca hacer `git add -f` sobre rutas ignoradas.

## Estados permitidos para evidencias

- `CONFIRMED`
- `CANDIDATE`
- `INSUFFICIENT_EVIDENCE`
- `REQUIRES_HUMAN_REVIEW`

Para diferencias ERP:

- `EXPECTED`
- `UNDOCUMENTED`
- `RISK`
- `CRITICAL`
- `REQUIRES_HUMAN_REVIEW`

## Gates de merge

No fusionar a `sprint/001-erp-drift` hasta que:

1. tests locales pasen;
2. no existan datos privados en el diff;
3. el cambio sea idempotente;
4. no escriba producción;
5. rollback/sandbox continúen funcionando;
6. revisión independiente complete PASS o PASS_WITH_WARNINGS aceptado.

No fusionar a `main` durante Sprint 001.
