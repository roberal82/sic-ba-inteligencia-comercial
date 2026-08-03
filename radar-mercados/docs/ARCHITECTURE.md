# Arquitectura

## Vista general

```text
[ Frontend HTML/CSS/JS ]  <-- fetch -->  [ FastAPI backend ]  <-- httpx -->  [ Fuentes externas ]
                                                |
                                        [ SQLAlchemy ]
                                                |
                                   [ PostgreSQL / SQLite ]

                                        [ APScheduler ]  --(jobs)-->  refresca mercados/eventos,
                                                                       limpia historico, respalda DB
```

## Backend

- **FastAPI** expone la API bajo `/api`, con documentación OpenAPI automática en
  `/api/docs`.
- **Capa de servicios** (`app/services/`): un módulo por país/clase de activo
  (`brazil_service.py`, `paraguay_service.py`, `argentina_service.py`,
  `global_markets_service.py`, `commodities_service.py`, `crypto_service.py`,
  `geopolitics_service.py`), más `analysis_service.py` (motor de reglas) y
  `scenario_service.py` (perfiles de asignación). Cada servicio de mercado:
  1. En `APP_MODE=demo`, devuelve directamente el subconjunto demostrativo
     correspondiente (`fallback_service.py`).
  2. En `APP_MODE=production`, intenta la fuente real vía `services/base.py`
     (timeout configurable, reintentos con backoff exponencial). Si falla, cae al
     mismo dato demostrativo marcando el motivo en el campo `source`.
- **Capa de repositorios** (`app/repositories/market_repository.py`): agrega los
  resultados de todos los servicios en paralelo (`asyncio.gather`), aplica cache con
  TTL y persiste snapshots en la base de datos para alimentar el historial.
- **Capa de modelos/esquemas**: SQLAlchemy (`app/models/`) para persistencia,
  Pydantic (`app/schemas/`) para validación y documentación de la API. Comparten la
  misma forma de datos.
- **Jobs** (`app/jobs/scheduler.py`): APScheduler embebido (sin broker externo) con
  tareas de mercados, eventos, limpieza y respaldo. Su estado (última ejecución,
  duración, error) se expone en `/api/system/status`.
- **Motor de análisis** (`analysis_service.py`): reglas explícitas tipo
  `si <condiciones sobre indicadores/eventos> entonces <lectura>`. No genera texto
  libre ni predicciones: si no se cumplen las condiciones de una regla, esta
  simplemente no aparece en la respuesta. Ver ejemplos en el propio código y en la
  sección 10 del prompt original.

## Frontend

HTML + CSS + JavaScript modular (sin paso de build), con Chart.js y Leaflet
**vendorizados localmente** (`frontend/static/vendor/`) para no depender de un CDN
externo en producción:

- `api.js`: resolución del backend (mismo origen por defecto, configurable) y
  respaldo local (`static/data/demo_dashboard.json`) si la API es inalcanzable.
- `charts.js`: construcción de los 18 gráficos/paneles del dashboard a partir de
  datos reales o demostrativos, sin inventar series temporales cuando no hay
  historial suficiente (ver `docs/DATA_SOURCES.md`).
- `map.js`: mapa Leaflet con filtros por país/severidad/tipo.
- `export.js`: exportación de gráficos a PNG y de tablas/series a CSV.
- `main.js`: orquestación, con cada sección del panel renderizada de forma aislada
  (`safe(...)`) para que el fallo de un widget no derribe el resto del panel.

## Por qué no React/TypeScript

El prototipo original ya incluía un frontend HTML funcional. Se optó por mantenerlo y
modularizarlo (alternativa explícitamente aceptada) en lugar de reescribirlo en
React + Vite, priorizando velocidad de entrega y ausencia de paso de build. Una
migración a React/TypeScript es viable como siguiente iteración: los endpoints ya
devuelven JSON tipado (`schemas.py`) listo para generar tipos TypeScript.

## Decisiones de infraestructura

- **SQLite por defecto / PostgreSQL en Docker**: desarrollo local sin dependencias
  externas; producción con PostgreSQL vía `DATABASE_URL`.
- **Redis opcional**: si `REDIS_URL` no está configurado o no responde, se usa cache
  en memoria del proceso automáticamente (ver `app/core/cache.py`).
- **APScheduler en vez de Celery**: no requiere broker adicional; suficiente para la
  cadencia de actualización especificada (minutos, no segundos).
