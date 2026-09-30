# SIC-BA — Operaciones

## Entorno Python autorizado

```
C:\BLANCO_ASOCIADOS_AI\.venv\Scripts\python.exe
```

No usar Python de WindowsApps, LibreOffice, PostgreSQL, Tesseract ni otros
intérpretes del sistema.

## Comandos frecuentes

```powershell
# Regresión completa
& "C:\BLANCO_ASOCIADOS_AI\.venv\Scripts\python.exe" -m pytest -q

# Panel operativo (solo lectura)
& "C:\BLANCO_ASOCIADOS_AI\.venv\Scripts\python.exe" run_ops_panel.py `
  --config config\ops_panel.example.json

# Release gate técnico
& "C:\BLANCO_ASOCIADOS_AI\.venv\Scripts\python.exe" run_release_gate.py `
  --evidence config\release_candidate.example.json --pretty

# Simulación F5 (cutover)
& "C:\BLANCO_ASOCIADOS_AI\.venv\Scripts\python.exe" run_f5.py `
  --manifest config\f5_cutover.example.json --pretty
```

## Mapa de worktrees (`C:\BLANCO_ASOCIADOS_AI`)

| Worktree | Rama | Rol |
|---|---|---|
| `repo-control` | `main` | Nunca se toca durante sprints |
| `claude-builder` | `fix/sprint001-header-rows` | BUILDER (Claude) |
| `codex-review` | `agent/codex-drift` | QA adversarial (Codex) |
| `gemini-validator` | `agent/gemini-drift` | Validación cruzada (Gemini) |
| `hermes-worker` | `agent/hermes-drift` | Metadata de snapshots privados |
| `sprint-control` | `sprint/001-erp-drift` | Integración Sprint 001 |
| `production-readiness` | `sprint/005-production-readiness` | Este sprint |

## Ramas de integración

- `feature/f4-orchestration-dryrun` — integración técnica activa (Sprints
  001-004 ya fusionados). Este sprint (005) se desarrolla aparte y se integra
  aquí solo cuando la regresión completa está verde.
- `main` — protegida. No recibe cambios hasta que los gates productivos estén
  completos y haya aprobación explícita.

## Workflows de CI (`.github/workflows/`)

| Workflow | Dispara en | Qué valida |
|---|---|---|
| `f4-orchestration-tests.yml` | PR/push a orquestación | Unit tests F4/Sprint002, dry-run, idempotencia, rollback de sandbox |
| `f5-cutover-tests.yml` | PR/push a cutover | Unit tests F5, dry-run de ejemplo |
| `financial-governance-tests.yml` | PR/push a gobierno financiero | Tests + imports CLI compatibles |
| `pipeline-governance-tests.yml` | PR/push a pipeline comercial | Tests de forecast/pipeline |
| `production-readiness-tests.yml` | PR/push a gates/writer/cutover/observabilidad/panel | Compila + corre esos tests + panel + release gate |
| `security-check.yml` | PR/push a `src/**`/`run_*.py` | Escaneo de patrones peligrosos, secretos, payloads privados |
| `release-candidate.yml` | PR/push a rama de release | Regresión completa + release gate + verificación de payloads privados + whitespace |

## Antes de fusionar a `feature/f4-orchestration-dryrun`

1. Regresión completa en verde (`pytest -q`).
2. `python -m compileall -q src`.
3. `git diff --check` sin hallazgos.
4. `run_release_gate.py` sobre evidencia real (no solo el ejemplo).
5. Ningún dato privado en el diff (`git status` + revisión manual del diff).
