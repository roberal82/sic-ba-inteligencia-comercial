# Despliegue

## Local (sin Docker)

Ver README. Adecuado para desarrollo y demostraciones.

## Docker / VPS Linux

```bash
cd radar-mercados/infra
cp ../.env.example .env
# Editar .env: definir POSTGRES_PASSWORD como minimo, y APP_MODE=production si
# corresponde, mas las claves de proveedores que se hayan contratado.
docker compose up --build -d
```

Servicios: `db` (PostgreSQL 16), `redis` (cache opcional, se usa automáticamente si
está disponible), `backend` (FastAPI/uvicorn, corre `alembic upgrade head` al
arrancar), `nginx` (puerto 80, sirve el frontend estático y hace proxy de `/api/` al
backend).

> **Estado de verificación de esta entrega**: `docker compose config` valida la
> sintaxis y la resolución de variables de entorno correctamente (ver salida en el
> historial de desarrollo). El build real de las imágenes (`docker compose up
> --build`) **no pudo ejecutarse** en el entorno de esta sesión porque no había un
> daemon de Docker disponible (`/var/run/docker.sock` inexistente). Se recomienda
> ejecutar `docker compose up --build` como primer paso de validación en un entorno
> con Docker real antes de considerar el despliegue como probado end-to-end.

## Render / Railway

- **Backend**: desplegar `backend/` como servicio web con `Dockerfile` propio, o
  como servicio Python nativo con `pip install -r requirements.txt` y comando de
  arranque `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port
  $PORT`. Agregar una base PostgreSQL administrada y configurar `DATABASE_URL` con
  su cadena de conexión.
- **Frontend**: se puede servir de dos formas:
  1. Dejar que el propio backend lo sirva (montaje `/static` + `/` en
     `app/main.py`), desplegando solo el backend.
  2. Desplegar `frontend/` como sitio estático independiente (usa
     `frontend/Dockerfile` + `frontend/nginx.frontend.conf`, o cualquier hosting
     estático), configurando la URL del backend en el campo "Configurar backend"
     del panel (persiste en el input; para hacerlo automático, editar
     `frontend/static/js/api.js` y fijar una URL por defecto).
- Configurar `CORS_ORIGINS` en el backend con el dominio real del frontend cuando
  estén en dominios distintos.

## Variables críticas en producción

- `APP_MODE=production`
- `DATABASE_URL` apuntando a PostgreSQL administrado
- `ADMIN_TOKEN` con un valor aleatorio largo (`openssl rand -hex 32`)
- `CORS_ORIGINS` con el dominio exacto del frontend (nunca `*` en producción)
- Claves de proveedores contratados, si aplica

## Backups

- SQLite (desarrollo): la tarea programada `backup` copia el archivo `.db` a
  `backend/backups/` diariamente.
- PostgreSQL (producción): usar el mecanismo de backup del proveedor administrado
  (snapshots de Render/Railway) o `pg_dump` programado a nivel de infraestructura;
  el job `backup` del scheduler detecta que el motor no es SQLite y no interfiere.

## Solución de problemas

| Síntoma | Causa probable | Acción |
|---|---|---|
| `/api/health` responde pero el panel muestra "Sin conexión al backend" | CORS mal configurado o backend en otro origen sin URL configurada en el panel | Revisar `CORS_ORIGINS` y el campo "Configurar backend" del panel |
| Todos los indicadores en `data_status: demo` con `APP_MODE=production` | Fuentes externas bloqueadas por firewall/proxy del hosting | Revisar logs del backend; cada fallo se registra con el motivo |
| `POST /api/admin/refresh` devuelve 503 | `ADMIN_TOKEN` no configurado | Definir `ADMIN_TOKEN` en el entorno del backend |
| Migraciones fallan al iniciar el contenedor backend | Base de datos no disponible aún | El `docker-compose.yml` ya usa `depends_on` con `condition: service_healthy` para `db`; verificar credenciales |
