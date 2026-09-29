# Sprint 002 — Integración operacional controlada

## Objetivo

Integrar el ERP Drift Engine y el control plane F4 a un flujo operativo **read-only + staging**, sin escribir ERP, Drive, PostgreSQL productivo ni `main`.

El Sprint 002 agrega:

1. adaptadores locales read-only;
2. staging aislado por `run_id`;
3. fingerprint manifest + hashes de fuentes;
4. idempotencia;
5. quarantine/rejected;
6. audit log saneado por ejecución;
7. rollback selectivo del staging;
8. conexión al control plane J01–J10;
9. bloqueo explícito si un modo `apply` llegara a quedar productivamente habilitable: no existe adaptador productivo en este sprint.

## Arquitectura

```text
fuentes locales read-only
        │
        ▼
CsvSourceAdapter
        │  SHA-256 antes/después
        ▼
StageRunStore
 ├─ staged/*.jsonl
 ├─ quarantine/*.jsonl
 ├─ meta/*.json
 ├─ audit/events.jsonl
 ├─ run_meta.json
 └─ result.json
        │
        ▼
run_manifest() / J01–J10
        │
        ├─ L4 permanece gate independiente
        ├─ L7 permanece gate independiente
        └─ producción no implementada
```

## Guardrail de inferencia

La presencia de un archivo puede derivar únicamente disponibilidad de:

- `sales_ready`
- `purchases_ready`
- `pipeline_ready`
- `documents_ready`

No puede derivar automáticamente:

- `master_resolution_ready`
- `relation_candidates_ready`
- `cost_evidence_ready`
- `bi_ready`
- L4
- L7
- aprobación humana
- rollback real

Por tanto, un CSV no convierte una relación o costo candidato en confirmado.

## Idempotencia

La huella de ejecución se calcula sobre:

- manifest completo;
- SHA-256 de cada fuente leída.

Repetir el mismo `run_id` con igual manifest y mismas fuentes es idempotente. Reutilizar el mismo `run_id` con cualquier cambio de fuente o manifest falla cerrado.

## Quarantine

En staging, una fila se cuarentena cuando:

- falta una clave declarada (`MISSING_KEY`);
- una misma clave reaparece con contenido distinto (`DUPLICATE_KEY_CONFLICT`).

Un duplicado exactamente idéntico se cuenta como `exact_duplicates` y no se duplica en staging.

La cuarentena no se publica como cero ni como dato confirmado.

## Audit log

El audit log conserva solo metadata operacional:

- secuencia;
- evento;
- dominio;
- conteos;
- hashes de fuente;
- outcome de gates.

No copia valores de clientes, proveedores, importes ni contenido de filas.

## CLI

Ejemplo:

```bash
python run_sprint002_stage.py \
  --manifest config/sprint002_manifest.example.json \
  --source-root data_clean \
  --stage-root sandbox/sprint002 \
  --mode stage \
  --pretty
```

Rollback:

```bash
python run_sprint002_stage.py \
  --stage-root sandbox/sprint002 \
  --rollback-run S2-STAGE-EXAMPLE
```

## Política de producción

Aunque `Mode.APPLY` reciba L4 PASS, L7 GO, rollback, aprobación e interlock, Sprint 002 devuelve:

`BLOCKED_PRODUCTION_ADAPTER_MISSING`

Esto es deliberado. No existe código de escritura productiva en este sprint.

## Criterio de cierre

Sprint 002 puede cerrarse cuando:

- tests F4 previos siguen PASS;
- tests Sprint 002 PASS;
- source path traversal bloqueado;
- hashes de fuentes permanecen intactos;
- idempotencia probada;
- conflicto de fingerprint probado;
- quarantine probado;
- rollback selectivo probado;
- L4/L7 siguen independientes;
- `apply` no puede convertirse en writer productivo;
- CI PASS en PR hacia `feature/f4-orchestration-dryrun`.
