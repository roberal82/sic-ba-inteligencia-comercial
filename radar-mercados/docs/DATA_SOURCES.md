# Fuentes de datos

Este documento distingue explícitamente qué fuentes están **realmente conectadas**
(código de integración real, sin necesidad de credenciales) de las que están
**pendientes** (requieren clave contratada o no existe API pública gratuita
documentada). Esta misma información se expone en vivo en `GET /api/sources` y en la
sección "Fuentes y estado de conexión" del panel.

> Nota sobre esta entrega: el entorno de desarrollo de esta sesión bloquea por
> política de red las conexiones salientes hacia dominios externos (incluidas todas
> las fuentes listadas abajo), de modo que no fue posible verificar en vivo las
> respuestas exactas de cada API durante el desarrollo. El código de integración se
> escribió contra los contratos documentados de cada API pública y con manejo
> defensivo de errores (timeout, reintentos, parseo tolerante a formato inesperado);
> ante cualquier fallo cae automáticamente al dato demostrativo correspondiente, por
> lo que el panel nunca queda roto. Se recomienda verificar la conectividad real la
> primera vez que se ejecute con `APP_MODE=production` en un entorno con acceso
> normal a Internet, revisando `GET /api/sources` y los logs.

## Conectadas (API pública, sin clave)

| Fuente | Módulo | Cobertura | Notas |
|---|---|---|---|
| Banco Central do Brasil — API SGS | `brazil_service.py` | Selic, IPCA, USD/BRL (PTAX) | `https://api.bcb.gov.br/dados/serie/` |
| BCRA — API de Estadísticas v3.0 | `argentina_service.py` | Reservas internacionales, dólar mayorista (A3500) | `https://api.bcra.gob.ar/estadisticas/v3.0/monetarias` |
| CoinGecko | `crypto_service.py` | Bitcoin, Ethereum | `https://api.coingecko.com/api/v3/simple/price` |
| stooq.com | `global_markets_service.py`, `commodities_service.py` | S&P 500, Dow Jones, Nasdaq, VIX, EUR/USD, oro, plata, WTI, cobre | Cotizaciones con retardo (~15 min), uso no comercial |
| GDELT Doc API | `geopolitics_service.py` | Eventos geopolíticos (titulares recientes) | Severidad/probabilidad inferidas heurísticamente por palabras clave; se documenta como estimación de menor confianza |

## Pendientes de proveedor contratado (requieren API key)

| Fuente | Uso previsto | Variable de entorno |
|---|---|---|
| Alpha Vantage | Cotizaciones adicionales, indicadores técnicos | `ALPHA_VANTAGE_API_KEY` |
| Twelve Data | Índices, acciones, forex adicionales, volumen negociado | `TWELVE_DATA_API_KEY` |
| Polygon.io | Datos de mercado en tiempo real, volumen negociado | `POLYGON_API_KEY` |
| News API | Noticias adicionales para el motor de eventos | `NEWS_API_KEY` |
| FRED (Federal Reserve) | Series macro de EE.UU. (Treasury 10Y con mayor precisión, DXY) | `FRED_API_KEY` |

Sin la clave correspondiente, `GET /api/sources` marca estas fuentes como
`pendiente_credenciales` y los indicadores asociados se sirven como datos
demostrativos (Ibovespa, acciones brasileñas, Merval, riesgo país, MEP/CCL, bonos,
Treasury 10Y, DXY, MSCI EM, Brent, soja Chicago, volumen negociado).

## Sin API pública documentada (limitación estructural, no de credenciales)

| Fuente | País | Motivo |
|---|---|---|
| Banco Central del Paraguay | Paraguay | Solo publica paneles/portales web; no se identificó una API JSON pública y documentada al momento de esta versión. |
| Bolsa de Valores de Asunción (BVPASA) | Paraguay | Mismo caso: sin API pública documentada. |
| BYMA / CNV / INDEC | Argentina | Sin API gratuita identificada para Merval, bonos, riesgo país oficial o inflación INDEC en tiempo real. |

Para estas fuentes, **todos** los indicadores se marcan siempre como `data_status:
"demo"`, independientemente de `APP_MODE`, y `paraguay_service.py` documenta este
motivo explícitamente en el campo `source` de cada registro
(`"Fuente sin API publica documentada (pendiente convenio BCP / BVPASA)"`). Opciones
para resolverlo a futuro: convenio de datos con el BCP/BVPASA, scraping autorizado de
sus portales públicos, o contratar un proveedor de datos de mercado que las cubra
(Twelve Data/Polygon suelen tener cobertura limitada de mercados latinoamericanos
pequeños; conviene confirmar antes de contratar).

## Historial temporal (evolución, volatilidad, correlación)

Los gráficos que requieren series temporales (evolución normalizada de índices, oro
vs. dólar, petróleo, volatilidad histórica real, correlación entre activos) se
alimentan de `GET /api/markets/history/{symbol}`, que lee los snapshots guardados por
la tarea programada `refresh_markets` (cada `REFRESH_MINUTES_MARKETS` minutos, 15 por
defecto). En una instalación recién iniciada esa tabla está vacía o casi vacía; en
ese caso el endpoint responde `sufficient_history: false` y el frontend muestra un
aviso explícito en vez de fabricar una serie. El historial se completa solo, sin
intervención manual, a medida que el scheduler corre.
