# SIC-BA — Seguridad

## Datos privados

Nunca se versionan: credenciales, IDs internos de Drive, extractos bancarios,
CxC/CxP, documentos de clientes/proveedores, copias del ERP. Viven bajo
`C:\BLANCO_ASOCIADOS_AI\private-data\` (fuera del repo) y `.gitignore` cubre
`private-data/`, `data_private/`, `local_private/`, `*.key`, `*.pem`,
`credentials*`, `secrets*`, `*.p12`, `*.pfx`, más las salidas locales del
Sprint multiagente.

`security-check.yml` (CI) falla el build si aparece cualquier archivo con esos
patrones en `git ls-files`.

## Escritura de archivos

Todo el motor de diff ERP (`src/erp_diff_engine/security.py`) y el writer
(`src/writer/adapters.py`, `src/writer/store.py`) escriben mediante patrones
atómicos (`tempfile` + `os.replace`) y validan que la ruta de salida no se
escape del directorio esperado (`safe_output_path`, `_validate_name` con
regex `^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$` para `run_id`/`op_id`/`domain`).

## Patrones prohibidos (escaneados en CI)

`shell=True`, `pickle.load`, `yaml.load` sin `SafeLoader`, `os.system`,
`eval`/`exec`. A la fecha de este documento, ninguno está presente en `src/`
ni en los `run_*.py`.

## Secretos

- Ningún módulo lee variables de entorno para credenciales (solo
  `SIC_BA_PRODUCTION_WRITE`, que es un interlock, no un secreto).
- `src/observability/log.py` (`RunLogEntry`) rechaza campos cuyo nombre
  sugiera un secreto (`password`, `token`, `api_key`, `credential`, `secret`)
  antes de escribir cualquier log — `SecretLikeFieldError`.
- `RunLogger` escribe JSONL append-only; nunca reescribe eventos previos.

## Escritura productiva

`src.writer.NullProductionAdapter` es el único adaptador "real" para el ERP
productivo, y su única función es lanzar `WriterAdapterNotConfigured` ante
cualquier intento de uso. Esto es deliberado, no un bug pendiente: es la
manera en que el código garantiza, en tiempo de ejecución, que "ningún agente
escribe en producción" (regla central de `AGENTS.md`).

## CSV / inyección de fórmulas

Las salidas CSV/Excel de dashboards (`src/dashboard_*.py`) consumen
`data_clean/` ya validado por los pipelines de gobierno financiero/comercial;
no se interpolan valores de usuario final directamente en fórmulas. Si se
agregan nuevas exportaciones a Excel/CSV a partir de texto libre, deben
neutralizar prefijos `=`, `+`, `-`, `@` antes de escribir (no aplica hoy
porque no existe ese flujo).

## Revisión continua

`security-check.yml` corre en cada PR que toque `src/**` o `run_*.py`, más en
push a `sprint/005-production-readiness` y `feature/f4-orchestration-dryrun`.
