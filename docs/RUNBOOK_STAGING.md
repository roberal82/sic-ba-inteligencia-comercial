# SIC-BA — Runbook de staging en notebook

## Alcance

Este runbook opera únicamente sobre copias locales/read-only y staging. No contiene comandos de escritura al ERP productivo.

## 1. Preparar fuentes privadas

Mantener archivos reales fuera del repositorio público, por ejemplo:

```text
C:\BLANCO_ASOCIADOS_AI\private-data\input\
C:\BLANCO_ASOCIADOS_AI\private-data\staging\
C:\BLANCO_ASOCIADOS_AI\private-data\logs\
```

Nunca copiar esos archivos al repositorio Git.

## 2. Ejecutar Sprint 002

Desde el repositorio/worktree validado:

```powershell
& "C:\BLANCO_ASOCIADOS_AI\.venv\Scripts\python.exe" `
  .\run_sprint002_stage.py `
  --manifest "C:\BLANCO_ASOCIADOS_AI\private-data\config\sprint002.json" `
  --source-root "C:\BLANCO_ASOCIADOS_AI\private-data\input" `
  --stage-root "C:\BLANCO_ASOCIADOS_AI\private-data\staging\sprint002" `
  --mode stage `
  --pretty
```

## 3. Revisar resultados

Por cada `run_id` revisar:

```text
run_meta.json
result.json
staged\
quarantine\
meta\
audit\events.jsonl
```

Criterios:

- ninguna fuente cambia de hash durante lectura;
- quarantine no se interpreta como cero;
- `DUPLICATE_KEY_CONFLICT` requiere saneamiento o revisión;
- `MISSING_KEY` no se promueve a staging;
- audit no contiene valores de negocio;
- J09 y J10 siguen bloqueados si L4 no está PASS.

## 4. Repetición idempotente

Repetir el mismo `run_id` con las mismas fuentes y manifest debe conservar la misma huella de ejecución.

Si cambia cualquier fuente o el manifest, usar un `run_id` nuevo. El sistema falla cerrado si se intenta reutilizar el anterior.

## 5. Rollback de staging

```powershell
& "C:\BLANCO_ASOCIADOS_AI\.venv\Scripts\python.exe" `
  .\run_sprint002_stage.py `
  --stage-root "C:\BLANCO_ASOCIADOS_AI\private-data\staging\sprint002" `
  --rollback-run "<RUN_ID>"
```

El rollback elimina solo el directorio del `run_id` indicado.

## 6. Release gate

El gate técnico puede ejecutarse con evidencia local privada equivalente a `config/release_candidate.example.json`:

```powershell
& "C:\BLANCO_ASOCIADOS_AI\.venv\Scripts\python.exe" `
  .\run_release_gate.py `
  --evidence "C:\BLANCO_ASOCIADOS_AI\private-data\config\release_candidate.json" `
  --pretty
```

`RC_READY` significa staging técnicamente listo. No significa autorización de producción.

## 7. Producción

No ejecutar cutover si falta cualquiera de estos puntos:

- L4 PASS;
- L7 GO;
- rollback real probado;
- aprobación humana explícita;
- interlock productivo explícito;
- writer productivo implementado y auditado en un sprint separado.

El Release Candidate actual no contiene ese writer.

## Recuperación ante error

1. detener el runner;
2. no modificar las fuentes;
3. conservar `run_meta.json` y audit;
4. revisar quarantine;
5. si el run quedó incompleto, hacer rollback selectivo;
6. corregir manifest o fuente en copia;
7. ejecutar con un `run_id` nuevo.
