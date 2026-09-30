# SIC-BA — Deployment

## Estado actual

No existe un "deploy a producción" en este repositorio: no hay adaptador
productivo real (`src.writer.NullProductionAdapter`), por lo que
`production_ready` del release gate no puede ser verdadero hoy sin importar
cuántos gates pasen (ver `src/orchestration/release_gate.py`).

Lo que sí existe y se "despliega" activamente:

1. **CI** (GitHub Actions, `.github/workflows/`): valida cada PR/push contra
   las ramas de integración. Ver la lista de workflows en `docs/OPERATIONS.md`.
2. **Staging local aislado** (`private-data/staging/`, `sandbox/`): usado por
   Sprint 002 y por las pruebas del writer. Nunca es un entorno compartido.
3. **Dashboards Streamlit** (`src/dashboard_*.py`): consumen `data_clean/`
   local, nunca escriben al ERP.

## Entornos

| Entorno | Dónde | Qué puede hacer |
|---|---|---|
| Desarrollo/test | Worktrees en `C:\BLANCO_ASOCIADOS_AI\*` | Todo: tests, sandbox, dry-run |
| CI (GitHub Actions) | `ubuntu-latest` | Compila, corre tests, evalúa gates sobre evidencia de ejemplo |
| Staging | `private-data/staging/`, `sandbox/` | Solo lectura de fuentes reales + escritura aislada local |
| Producción (ERP real) | Fuera de este repositorio | **No accesible** desde este código; `NullProductionAdapter` lo garantiza |

## Variable de interlock

`SIC_BA_PRODUCTION_WRITE` — debe ser exactamente `ENABLED` para que
`WriterInterlock.env_enabled` sea verdadero. Es una condición **necesaria
pero no suficiente**: por sí sola, sin L4 PASS + L7 GO + rollback probado +
aprobación humana + ventana de cutover + snapshot listo, `apply_authorized`
sigue siendo falso (`src/writer/models.py`).

## Cuándo este documento deja de ser cierto

Cuando exista un `ProductionAdapter` real distinto de `NullProductionAdapter`
y `SandboxUpsertAdapter`, y esté conectado a `config/release_candidate.example.json`
vía `production_adapter_configured=true`. Hasta entonces, "deployment a
producción" no es una operación que este repositorio pueda ejecutar.
