# Seguridad

## Gestión de secretos

- Todas las claves de proveedores y credenciales se leen desde variables de entorno
  (`app/core/config.py`, `pydantic-settings`). Ninguna clave está hardcodeada.
- `backend/.env` está excluido de git (`.gitignore`); se distribuye `.env.example`
  sin valores reales.
- El frontend nunca recibe ni almacena claves de API: todas las llamadas a fuentes
  externas ocurren exclusivamente en el backend.
- Los logs (`app/core/logging.py`) filtran líneas que parecen contener claves,
  tokens, contraseñas o cabeceras de autorización antes de imprimirlas.

## Endpoint administrativo

`POST /api/admin/refresh` requiere el header `X-Admin-Token` igual a `ADMIN_TOKEN`.
Si `ADMIN_TOKEN` no está configurado, el endpoint responde `503` en vez de quedar
abierto sin protección.

## CORS

Configurable vía `CORS_ORIGINS` (lista separada por comas). Por defecto `*` para
facilitar desarrollo y demos; en producción debe restringirse al dominio exacto del
frontend.

## Rate limiting

`slowapi` aplica un límite global configurable (`RATE_LIMIT_PER_MINUTE`, 120 por
defecto) por IP de origen, para mitigar abuso básico.

## Cabeceras HTTP de seguridad

`SecurityHeadersMiddleware` agrega en toda respuesta: `X-Content-Type-Options:
nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy:
strict-origin-when-cross-origin`, `Permissions-Policy` restrictiva. Nginx
(`infra/nginx.conf`, `frontend/nginx.frontend.conf`) agrega las mismas cabeceras a
nivel de proxy/estáticos.

## Validación de entrada

Todos los parámetros de los endpoints están tipados con Pydantic/FastAPI (paths,
queries y cuerpos). Los símbolos y países se validan contra listas conocidas donde
corresponde (`VALID_COUNTRIES` en `routes_markets.py`), devolviendo `404`/`422` en
vez de propagar errores no controlados.

## Manejo de errores de fuentes externas

Todas las llamadas a APIs externas pasan por `services/base.py`, con timeout
(`HTTP_TIMEOUT_SECONDS`), reintentos con backoff exponencial
(`HTTP_MAX_RETRIES`) y captura explícita de excepciones. Ningún fallo de una fuente
externa se propaga como error 500 al cliente: siempre cae al dato demostrativo
correspondiente, marcado como tal.

## Dependencias

`requirements.txt` fija versiones exactas de todas las dependencias del backend
(sin rangos abiertos), para builds reproducibles y para poder auditar
actualizaciones de seguridad de forma controlada. Se recomienda ejecutar `pip-audit`
o similar periódicamente en un pipeline de CI.

## Base de datos

- SQLite en desarrollo (archivo local, sin exposición de red).
- PostgreSQL en Docker con credenciales por variable de entorno
  (`POSTGRES_PASSWORD` obligatorio, sin valor por defecto — `docker-compose.yml`
  falla explícitamente si no se define).
- Sin credenciales de base de datos hardcodeadas en ningún archivo versionado.

## Alcance no cubierto en esta versión

- No incluye autenticación de usuarios ni roles (el panel es de solo lectura y
  público por diseño; el único endpoint de escritura, `/api/admin/refresh`, está
  protegido por token). Si se requiere multiusuario con permisos, es un desarrollo
  adicional a planificar.
- No incluye WAF ni protección DDoS de borde: en producción se recomienda ponerlo
  detrás de un proveedor con esas capacidades (Cloudflare, el balanceador del PaaS
  elegido, etc.).
