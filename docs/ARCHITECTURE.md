# SIC-BA — Arquitectura técnica

## Visión general

SIC-BA es un sistema de inteligencia comercial que convive con un ERP legacy
(ADMINISTRACION 2026) durante una migración planificada. El repositorio nunca
escribe en el ERP productivo por sí mismo; todo lo que existe hoy son
**decisiones** (gates, simuladores) y **staging aislado** (nunca producción).

Repositorio: `roberal82/sic-ba-inteligencia-comercial`.
Workspace multiagente: `C:\BLANCO_ASOCIADOS_AI` (varios worktrees Git sobre el
mismo repo, uno por rol/rama — ver `AGENTS.md`).

## Módulos por capa

### Gobierno financiero (evita inferencias, Sprints 001-004)

- `src/financial_governance.py` — `FinancialGate` liviano: bloquea que CRM,
  alertas, márgenes y scoring **inventen** relaciones financieras cuando no
  hay cierre oficial. No es el gate de producción (ver `src/gates/`).
- `src/pipeline_governance.py`, `src/profitability_governance.py` — forecast y
  margen solo se muestran cuando hay evidencia documentada; si no, `N/D`.
- `src/score_clientes.py`, `src/crm.py` — scoring comercial sin componente de
  mora ni riesgo de crédito inferido.

### Motor de diferencias ERP (Sprint 001)

`src/erp_diff_engine/` — compara BASE vs CURRENT de forma read-only:
`loader.py` (nunca escribe), `security.py` (path traversal, escritura atómica,
sha256), `row_diff.py`/`structure_diff.py`/`formula_diff.py` (detección),
`classify.py` (severidad), `config.py` (modos `keyed`/`positional`/`multiset`,
fail-closed ante un modo desconocido).

### Orquestación y staging (Sprint 002-003)

- `src/orchestration/adapters.py` — adaptadores **read-only** de fuentes CSV.
- `src/orchestration/stage_store.py` — `StageRunStore`: staging aislado por
  `run_id`, fingerprint de ejecución, cuarentena de filas inválidas, rollback
  por `run_id` (`rollback()` borra únicamente ese run).
- `src/orchestration/operational.py` — corre Sprint 002 completo; incluso en
  `Mode.APPLY` solo lee fuentes y escribe en `stage_root`
  (`production_adapter_present: False` explícito).
- `src/orchestration/release_gate.py` — `evaluate_release_candidate()`:
  agrega evidencia técnica + gates financieros/humanos/writer/adaptador en un
  único veredicto (`technical_status`, `production_status`,
  `production_ready`). Ver `docs/L4_GATE.md` y `docs/L7_GATE.md`.

### Gates formales L4/L7 (Sprint 005)

- `src/gates/l4_evidence.py` — `FinancialGateEvidence` + `evaluate_l4()`.
  Fail-closed: sin los ~10 campos obligatorios, nunca hay `PASS`.
- `src/gates/l7_decision.py` — `L7Inputs` + `evaluate_l7()`. Depende
  técnicamente de L4 PASS + integridad + rollback + smoke + UAT + manifest +
  aprobación humana con identidad.

### Writer productivo (Sprint 005)

`src/writer/` — ver `docs/ROLLBACK_RUNBOOK.md` para el flujo completo:

- `models.py` — `WriteMode` (DRY_RUN/STAGE/APPLY), `WriterInterlock`
  (default totalmente deshabilitado), `OperationSpec`/`OperationRecord`/`RunResult`.
- `adapters.py` — `NullProductionAdapter` (bloquea todo; es el default real
  para el ERP productivo) y `SandboxUpsertAdapter` (para pruebas locales).
- `store.py` — `WriterRunStore`: persistencia de runs, idempotencia por
  `run_id` + fingerprint de operaciones.
- `engine.py` — `ProductionWriter.execute()`: preflight, batch limit,
  timeout, reintentos acotados, checksum antes/después, detección de
  escritura parcial.
- `rollback.py` — `rollback_run()`: fail-closed ante modificación externa
  concurrente, idempotente, nunca toca otro `run_id`.

### Cutover (Sprint 005, sobre F5 de Sprint 003/004)

- `src/cutover/models.py`/`simulator.py` — simulación pura de los 10 pasos
  del runbook F5 (sin mutaciones).
- `src/cutover/engine.py` — `CutoverEngine`: construye el contexto F5 a
  partir de gates reales (`L4Result`/`L7Decision`) y expone
  `execute_go_live()`, que **siempre** lanza `CutoverEngineBlockedError` en
  este sprint (no hay adaptador productivo real).

### Observabilidad (Sprint 005)

`src/observability/log.py` — `RunLogger`/`RunLogEntry`: JSONL append-only,
con los campos y estados estándar del mandato. Falla cerrado si un nombre de
campo sugiere un secreto.

### Panel operativo (Sprint 005)

`src/ops_panel.py` + `run_ops_panel.py` — agrega TECHNICAL/L4/L7/WRITER/
ROLLBACK/CUTOVER/PRODUCTION/ADMIN 2026 en una vista de solo lectura.

## Datos privados

Todo dato real vive fuera del repo, bajo `C:\BLANCO_ASOCIADOS_AI\private-data\`
(`input/`, `staging/`, `snapshots/`, `outputs/`, `logs/`), ignorado por
`.gitignore`. `security-check.yml` verifica que nada de eso quede versionado.

## Lo que este repositorio deliberadamente NO hace

- No escribe en el ERP productivo (`NullProductionAdapter` es el único
  adaptador real que existe para ese destino).
- No infiere CxC/CxP/cheques/mora/riesgo/costos/márgenes/forecast sin
  evidencia documental.
- No fuerza `L4 PASS` ni `L7 GO` por la sola presencia de un flag.
- No archiva `ADMINISTRACION 2026` automáticamente.
