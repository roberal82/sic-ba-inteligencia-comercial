# Sprint 001 — Prompts de arranque

## Claude Code — BUILDER

Trabajas en la rama `agent/claude-drift` y en el worktree `C:\BLANCO_ASOCIADOS_AI\claude-builder`.

Lee primero `AGENTS.md` y `docs/sprints/SPRINT_001_ERP_DRIFT.md`.

Objetivo: implementar `ERP_DIFF_ENGINE` sin escribir producción ni versionar datos privados.

Requisitos mínimos:

- comparar estructura, hojas, columnas, filas, claves, valores, fórmulas y totales;
- aceptar rutas de entrada por CLI/config, nunca hardcodear rutas privadas;
- producir `diff_summary.json`, `diff_structure.json`, `diff_rows.csv`, `diff_formulas.csv` y `risk_report.md`;
- clasificación: `EXPECTED`, `UNDOCUMENTED`, `RISK`, `CRITICAL`, `REQUIRES_HUMAN_REVIEW`;
- idempotencia;
- tests con fixtures sintéticos solamente;
- soporte de celdas vacías, fechas, números PYG y fórmulas;
- ningún dato real de Blanco & Asociados en commits/tests.

Antes de terminar, ejecuta tests y deja un resumen de archivos modificados, pruebas realizadas y riesgos pendientes.

## Codex — QA ADVERSARIAL

Trabajas en `agent/codex-drift` / `C:\BLANCO_ASOCIADOS_AI\codex-review`.

Lee `AGENTS.md`, la especificación del Sprint y el código/diff producido por Claude. No asumas que la implementación es correcta.

Revisa como mínimo:

- falsos positivos y falsos negativos;
- archivos idénticos;
- hoja agregada/eliminada;
- fila agregada/eliminada/modificada;
- cambio de fórmula con mismo valor calculado;
- duplicados;
- nulos;
- encoding;
- fechas `dd/mm/yyyy`;
- importes PYG;
- idempotencia;
- paths y traversal;
- exposición accidental de datos privados;
- writes fuera de output/sandbox;
- manejo de errores.

Añade tests sintéticos cuando falten. Entrega `QA_REPORT.md` con `PASS`, `PASS_WITH_WARNINGS` o `FAIL` y evidencia concreta.

## Hermes Agent — DATA/BATCH

Trabajas en `agent/hermes-drift` / `C:\BLANCO_ASOCIADOS_AI\hermes-worker`.

No modifiques archivos fuente. Procesa únicamente copias colocadas en `C:\BLANCO_ASOCIADOS_AI\private-data\snapshots`.

Objetivo: producir inventario y manifest privado para BASE y CURRENT:

- nombre lógico;
- tipo;
- tamaño;
- hash SHA-256 cuando sea posible;
- hojas/tablas;
- conteo filas/columnas;
- encabezados;
- excepciones de lectura.

Salidas privadas:

- `manifest_base.json`
- `manifest_current.json`
- `inventory.csv`
- `exceptions.csv`

Estados: `CONFIRMED`, `CANDIDATE`, `INSUFFICIENT_EVIDENCE`, `REQUIRES_HUMAN_REVIEW`.

No subas manifests reales al repositorio público.

## Gemini — INDEPENDENT VALIDATOR

Trabajas en `agent/gemini-drift` / `C:\BLANCO_ASOCIADOS_AI\gemini-validator`.

No modifiques fuentes. Contrasta:

- manifests de Hermes;
- resultados del motor de Claude;
- reporte QA de Codex;
- copias privadas BASE y CURRENT.

Busca discrepancias, diferencias omitidas, clasificaciones de riesgo débiles y conclusiones no sustentadas.

Salida privada: `GEMINI_CROSSCHECK.md`.

Clasifica hallazgos como `CONFIRMED`, `DISPUTED` o `INSUFFICIENT_EVIDENCE`.

## Gate final del Sprint

No se autoriza merge a `main`. La rama de integración solo puede aceptar cambios cuando:

- no haya datos privados en Git;
- tests pasen;
- QA independiente no sea `FAIL`;
- las diferencias reales sean reproducibles;
- producción siga intacta.
