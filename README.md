# SIC-BA - Sistema de Inteligencia Comercial

Proyecto de Inteligencia Comercial para Blanco & Asociados.

## Objetivo

Transformar los reportes PDF generados por el ERP Valurq en información estratégica para la toma de decisiones.

El ERP seguirá siendo el sistema transaccional y contable.
El SIC-BA será el centro de comando gerencial.

## Arquitectura

```text
ERP Valurq
    ↓
Reportes PDF
    ↓
Google Drive
    ↓
Extractor Python
    ↓
Base Maestra SIC-BA
    ↓
Dashboard Ejecutivo
    ↓
IA Gerencial
```

## Módulos

### Financiero
- Cuentas por cobrar
- Cuentas por pagar
- Cheques diferidos
- Flujo de caja

### Comercial
- Ventas
- Clientes
- Cotizaciones
- Booking

### Operaciones
- Vehículos
- Combustible
- Gastos

### Inteligencia Artificial
- Alertas automáticas
- Score de clientes
- Riesgo financiero
- Predicción de flujo de caja

## Estructura del repositorio

```text
sic-ba-inteligencia-comercial/
├── src/
├── docs/
├── data_raw/
├── data_clean/
├── dashboard/
└── ia/
```

## Estado del Proyecto

`TECHNICAL = COMPLETE`, `PRODUCTION = WAITING_FOR_EXTERNAL_EVIDENCE`. Ver el
detalle completo y por qué en `docs/FINAL_STATUS.md`, y el mapa de módulos en
`docs/ARCHITECTURE.md`.

Sprints completados en `feature/f4-orchestration-dryrun`:

- **Sprint 001** — ERP Drift Engine (`src/erp_diff_engine/`).
- **Sprint 002** — Staging aislado, cuarentena, rollback por `run_id`
  (`src/orchestration/`).
- **Sprint 003** — Release Gate y regresión completa.
- **Sprint 004** — Gobierno financiero L4 fail-closed (CRM/scoring/forecast
  sin inferencias).
- **Sprint 005** — Writer productivo bloqueado por defecto, gates formales
  L4/L7, motor de cutover, observabilidad y panel operativo
  (`src/writer/`, `src/gates/`, `src/cutover/engine.py`,
  `src/observability/`, `run_ops_panel.py`).

## Panel operativo

```powershell
& "C:\BLANCO_ASOCIADOS_AI\.venv\Scripts\python.exe" run_ops_panel.py `
  --config config\ops_panel.example.json
```

Ver `docs/OPERATIONS.md` para el resto de comandos y `docs/L4_GATE.md` /
`docs/L7_GATE.md` / `docs/CUTOVER_RUNBOOK.md` / `docs/ROLLBACK_RUNBOOK.md`
para cada gate.

## Autor

Robert Benítez
Blanco & Asociados - Soluciones Integrales