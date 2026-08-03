# Radar Regional de Mercados

Plataforma web operativa para monitorear mercados de **Paraguay, Brasil, Argentina y
mercados globales**, junto con **riesgos geopolíticos georreferenciados**, **materias
primas, divisas, tasas, inflación, riesgo país, bonos, acciones y criptomonedas**, con un
**motor de análisis automatizado basado en reglas** y **escenarios orientativos de
inversión**. Educativa e informativa: no constituye asesoramiento financiero personalizado.

> Este proyecto es independiente del resto del repositorio (`sic-ba-inteligencia-comercial`,
> un sistema distinto de inteligencia comercial). Vive por completo dentro de esta carpeta,
> `radar-mercados/`, y no modifica ni depende de nada fuera de ella.

## Origen del proyecto

Este proyecto parte de un prototipo inicial (`_original_prototype/`, conservado intacto como
respaldo) que consistía en un backend FastAPI mínimo con dos endpoints de ejemplo y un
frontend HTML de una sola página con datos 100% hardcodeados. A partir de ahí se construyó
la version operativa actual: backend modular con integraciones reales documentadas,
fallback automático, motor de análisis, tareas programadas, base de datos, Docker y pruebas.

## Arquitectura

```text
radar-mercados/
├── _original_prototype/   # Copia de respaldo del prototipo inicial (sin modificar)
├── backend/                # API FastAPI (ver docs/ARCHITECTURE.md)
│   └── app/
│       ├── core/            # configuración, logging, db, cache, seguridad
│       ├── api/              # routers HTTP
│       ├── services/         # integraciones por país/clase de activo + motor de análisis
│       ├── models/            # modelos SQLAlchemy
│       ├── schemas/           # esquemas Pydantic (OpenAPI)
│       ├── repositories/      # agregación y persistencia
│       ├── jobs/               # tareas programadas (APScheduler)
│       └── tests/               # pytest
├── frontend/                # HTML/CSS/JS modular (Chart.js + Leaflet vendorizados)
├── infra/                   # docker-compose.yml + nginx.conf
├── scripts/run_local.sh     # arranque local sin Docker
└── docs/                     # ARCHITECTURE, DATA_SOURCES, API, DEPLOYMENT, SECURITY
```

### Por qué el frontend es HTML/CSS/JS modular y no React

El prototipo original ya traía un frontend HTML funcional (Chart.js + Leaflet). Se decidió
modularizarlo (separando `api.js`, `charts.js`, `map.js`, `export.js`, `main.js`) en vez de
reescribirlo en React/TypeScript, priorizando una base de código más simple de ejecutar sin
paso de build, con el mismo resultado visual y funcional. Es una alternativa explícitamente
aceptada para este tipo de proyecto; migrarlo a React/Vite queda documentado como mejora
futura en `docs/ARCHITECTURE.md`.

## Instalación y ejecución local (sin Docker)

Requiere Python 3.12 (probado también con 3.11).

```bash
cd radar-mercados
cp .env.example backend/.env   # ajustar variables si corresponde
bash scripts/run_local.sh
```

O manualmente:

```bash
cd radar-mercados/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Abrir `http://localhost:8000` (el backend sirve el frontend directamente). Documentación
interactiva de la API en `http://localhost:8000/api/docs`.

## Ejecución con Docker

```bash
cd radar-mercados/infra
cp ../.env.example .env   # definir POSTGRES_PASSWORD como minimo
docker compose up --build
```

- Panel: `http://localhost`
- API: `http://localhost/api`
- Documentación OpenAPI: `http://localhost/api/docs`

> Nota de esta entrega: los `Dockerfile`/`docker-compose.yml` fueron validados con
> `docker compose config` (sintaxis y resolución de variables correctas), pero el build
> real de las imágenes no pudo ejecutarse en el entorno de desarrollo de esta sesión por
> no contar con daemon de Docker disponible. Revisar `docs/DEPLOYMENT.md`.

## Variables de entorno

Ver `.env.example` para la lista completa y comentada. Ninguna clave se commitea al
repositorio; `backend/.env` está en `.gitignore`.

## Modo demo vs. producción

- `APP_MODE=demo`: todos los indicadores se sirven desde datos demostrativos, marcados
  explícitamente con `data_status="demo"`. Nunca falla por ausencia de conexión a Internet.
- `APP_MODE=production`: cada servicio intenta su fuente real primero; si falla (timeout,
  error HTTP, formato inesperado), cae automáticamente al mismo dato demostrativo,
  registrando el motivo en el campo `source` (p. ej. "... (BCB no disponible)"). El panel
  nunca se cae por completo por un solo proveedor caído.

## APIs disponibles

Ver `docs/API.md` para el detalle completo. Resumen:

```text
GET  /api/health
GET  /api/dashboard
GET  /api/markets
GET  /api/markets/{country}
GET  /api/markets/{country}/{category}
GET  /api/markets/history/{symbol}
GET  /api/events
GET  /api/events/map
GET  /api/analysis
GET  /api/scenarios
GET  /api/sources
GET  /api/system/status
POST /api/admin/refresh   (requiere header X-Admin-Token)
```

## Fuentes de datos

Ver `docs/DATA_SOURCES.md` para el detalle de qué fuentes están realmente conectadas
(sin necesidad de clave) y cuáles están documentadas como pendientes por no existir una
API pública gratuita (p. ej. BCP, BVPASA, BYMA) o por requerir una clave contratada
(Alpha Vantage, Twelve Data, Polygon.io, News API). El endpoint `GET /api/sources` expone
este mismo estado en tiempo real, y el panel lo muestra en la sección "Fuentes y estado
de conexión".

## Pruebas

```bash
cd radar-mercados/backend
source .venv/bin/activate
pytest app/tests -v
```

21 pruebas (endpoints principales, fallback por país, motor de reglas de análisis,
georreferenciación de eventos, salud del sistema). Ver `docs/API.md` para el detalle de
cobertura.

## Seguridad

Ver `docs/SECURITY.md`. Resumen: variables de entorno, sin claves en el frontend, CORS
configurable, rate limiting (slowapi), validación Pydantic en todos los endpoints,
cabeceras de seguridad HTTP, logs sin secretos, `.env` fuera de git.

## Limitaciones conocidas

- Los gráficos de evolución temporal (oro vs. dólar, petróleo, volatilidad histórica,
  correlación entre activos) requieren historial acumulado por las tareas programadas.
  En una instalación recién iniciada muestran un aviso explícito en vez de datos
  inventados, y se completan automáticamente con el uso continuo.
- Paraguay (BCP, BVPASA) y varios indicadores de Argentina (Merval, riesgo país, MEP/CCL,
  bonos) no tienen API pública gratuita documentada; se sirven como datos demostrativos
  hasta contratar un proveedor o conseguir un convenio de datos.
- El volumen negociado no está disponible en ninguna fuente gratuita conectada.
- Ver `docs/DATA_SOURCES.md` para el detalle completo.

## Mantenimiento

Las tareas programadas (`app/jobs/scheduler.py`) refrescan mercados y eventos, limpian
indicadores con más de 90 días y generan un respaldo diario de la base SQLite (en
PostgreSQL, el respaldo se gestiona a nivel de infraestructura). Su estado se puede
consultar en `GET /api/system/status`.
