# API

Documentación interactiva completa (OpenAPI/Swagger) disponible en tiempo de
ejecución en `/api/docs` (Swagger UI) y `/api/redoc` (ReDoc). Este documento resume
los endpoints principales.

Base URL local: `http://localhost:8000/api` (o `http://localhost/api` detrás de Nginx
en Docker).

## Salud y estado

| Endpoint | Descripción |
|---|---|
| `GET /api/health` | Estado básico, modo (`demo`/`production`) y hora del servidor. |
| `GET /api/system/status` | Estado de la base de datos, backend de cache (redis/memoria), y estado de las tareas programadas (última ejecución, próxima, duración, errores). |

## Dashboard

| Endpoint | Parámetros | Descripción |
|---|---|---|
| `GET /api/dashboard` | `country` (`regional`\|`brasil`\|`paraguay`\|`argentina`\|`global`), `period_days` | KPIs, indicadores, eventos, análisis y estado de fuentes en una sola respuesta, tal como lo consume el panel. |

## Mercados

| Endpoint | Parámetros | Descripción |
|---|---|---|
| `GET /api/markets` | `country`, `category` | Todos los indicadores, con filtros opcionales. |
| `GET /api/markets/{country}` | — | Indicadores de un país (`brasil`, `paraguay`, `argentina`, `global`). 404 si el país no existe. |
| `GET /api/markets/{country}/{category}` | — | Indicadores de un país filtrados por categoría (`indice`, `divisa`, `tasa`, `inflacion`, `commodity`, `cripto`, `bono`, `accion`, `reservas`, `riesgo_pais`, `volatilidad`). |
| `GET /api/markets/history/{symbol}` | `period_days` | Historial real acumulado por la tarea programada para ese símbolo. Responde `sufficient_history: false` si aún no hay al menos 2 puntos (nunca inventa datos). |

## Eventos geopolíticos

| Endpoint | Parámetros | Descripción |
|---|---|---|
| `GET /api/events` | `country`, `severity`, `event_type`, `sector`, `asset`, `since_days` | Lista de eventos georreferenciados con todos los campos (fuente, confianza, horizonte, activos/sectores afectados). |
| `GET /api/events/map` | `country`, `severity`, `event_type`, `sector`, `asset` | Versión reducida optimizada para marcadores del mapa. |

## Análisis y escenarios

| Endpoint | Parámetros | Descripción |
|---|---|---|
| `GET /api/analysis` | `scope` (`regional`\|`brasil`\|`paraguay`\|`argentina`\|`global`) | Salida del motor de reglas: solo se incluyen los análisis cuyas condiciones se cumplieron, más el resumen regional (siempre presente). Cada uno incluye siempre el disclaimer educativo. |
| `GET /api/scenarios` | — | Los tres perfiles de asignación orientativa (conservador, moderado, agresivo) con su explicación y disclaimer. |

## Fuentes y administración

| Endpoint | Parámetros | Descripción |
|---|---|---|
| `GET /api/sources` | — | Estado en vivo de cada fuente (`operativo`, `degradado`, `no_disponible`, `pendiente_credenciales`) con notas. |
| `POST /api/admin/refresh` | Header `X-Admin-Token` | Fuerza una actualización inmediata ignorando la cache. Requiere `ADMIN_TOKEN` configurado en el servidor; responde 503 si no lo está y 401 si el token no coincide. |

## Formato de un indicador (`MarketIndicator`)

```json
{
  "id": "uuid",
  "country": "brasil",
  "market": "BCB",
  "symbol": "SELIC",
  "name": "Tasa Selic",
  "category": "tasa",
  "value": 10.5,
  "unit": "%",
  "currency": "",
  "previous_value": 10.5,
  "change": 0.0,
  "change_percent": 0.0,
  "timestamp": "2026-08-03T18:00:00Z",
  "source": "Banco Central do Brasil (SGS)",
  "source_url": "https://api.bcb.gov.br/dados/serie/",
  "data_status": "live",
  "delayed_minutes": 0,
  "confidence": 0.9
}
```

`data_status` es siempre uno de: `live`, `delayed`, `estimated`, `demo`,
`unavailable`. El frontend nunca presenta un dato `demo` como si fuera en vivo.

## Pruebas automatizadas

`backend/app/tests/` (pytest + pytest-asyncio + FastAPI TestClient), 21 pruebas:

- `test_health.py`: salud y estado del sistema.
- `test_dashboard.py`: dashboard completo, filtros por país, 404 en país inválido,
  filtros de eventos, forma del mapa, escenarios, fuentes.
- `test_fallback.py`: forma de los datos demo, geolocalización válida de eventos,
  Paraguay siempre en modo demo, Brasil/Argentina/cripto en modo demo.
- `test_analysis.py`: cada regla del motor de análisis dispara solo cuando se
  cumplen sus condiciones, y no dispara cuando no se cumplen.

Ejecutar con `pytest app/tests -v` desde `backend/` (ver README para el entorno).
