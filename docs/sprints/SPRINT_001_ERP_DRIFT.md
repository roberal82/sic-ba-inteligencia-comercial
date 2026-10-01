# Sprint Multiagente 001 — ERP Drift Analysis

## Objetivo

Comparar una copia/snapshot base del ERP contra una copia actual y determinar exactamente qué cambió, sin escribir sobre producción.

## Alcance

Comparar como mínimo:

1. hojas agregadas/eliminadas;
2. nombres y orden de hojas;
3. filas y columnas;
4. encabezados y tipos de datos;
5. claves/duplicados;
6. fórmulas;
7. valores modificados;
8. totales de control;
9. cambios estructurales;
10. impacto potencial y nivel de riesgo.

## Entradas privadas

Las entradas no se versionan. Se esperan localmente bajo `private-data/snapshots/`:

- `ERP_BASE/` o una exportación equivalente del snapshot previo;
- `ERP_CURRENT/` o una exportación equivalente del estado actual.

Nunca incluir nombres/IDs privados en archivos públicos si no son necesarios para la lógica.

## Salidas esperadas

El motor debe producir, como mínimo:

- `diff_summary.json`
- `diff_structure.json`
- `diff_rows.csv`
- `diff_formulas.csv`
- `risk_report.md`

Las salidas reales con datos privados deben ir a `private-data/outputs/` o una ruta externa ignorada por Git.

## Secuencia de agentes

1. Hermes: inventario/metadata y manifest de las copias privadas.
2. Claude Code: implementación del motor de diferencias.
3. Codex: QA adversarial y tests adicionales.
4. Gemini: validación independiente de resultados.
5. ChatGPT + humano: consolidación y gate PASS/FAIL.

## Criterios de aceptación

- No se modifica el ERP productivo.
- Mismas entradas producen mismas salidas.
- Archivos idénticos generan cero diferencias materiales.
- Cambios controlados de hoja/fila/valor/fórmula son detectados.
- No se marca como confirmado lo que solo sea inferencia.
- El motor maneja celdas vacías, nulos, formatos de fecha y números PYG.
- Las excepciones quedan registradas y no abortan silenciosamente.
- Ningún dato privado aparece en commits, PRs o logs públicos.

## Estado inicial

`SPRINT_STARTED / PRODUCTION_FROZEN`

L4 y L7 no se alteran por el resultado de este sprint.
