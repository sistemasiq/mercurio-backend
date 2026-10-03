#!/bin/sh
# Arranque del contenedor del backend.
#
# 1. Espera a que PostgreSQL acepte conexiones.
# 2. Si la BD está vacía (no existe public.usuarios), la crea completa con
#    sql/schema_maestro.sql y, si SEED_DEMO=true, carga sql/seed_local.sql.
#    Una BD que ya tiene esquema NO se toca: las actualizaciones se aplican con
#    las migraciones de sql/migrations/.
# 3. Ejecuta el comando del contenedor (uvicorn por defecto).
set -eu

: "${DATABASE_URL:?DATABASE_URL es obligatoria}"

echo "[entrypoint] Esperando a PostgreSQL..."
intentos=0
until psql "$DATABASE_URL" -tAc 'SELECT 1' >/dev/null 2>&1; do
    intentos=$((intentos + 1))
    if [ "$intentos" -ge 60 ]; then
        echo "[entrypoint] PostgreSQL no respondió en 60 s" >&2
        exit 1
    fi
    sleep 1
done

existe=$(psql "$DATABASE_URL" -tAc "SELECT to_regclass('public.usuarios') IS NOT NULL")
if [ "$existe" = "f" ]; then
    echo "[entrypoint] BD vacía: aplicando sql/schema_maestro.sql"
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -q -f sql/schema_maestro.sql
    if [ "${SEED_DEMO:-false}" = "true" ]; then
        echo "[entrypoint] SEED_DEMO=true: cargando sql/seed_local.sql"
        psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -q -f sql/seed_local.sql
    fi
else
    echo "[entrypoint] La BD ya tiene esquema; no se inicializa"
fi

# Administrador de sistema inicial para poder entrar a la app. Solo se crea si el
# correo no existe: si después se cambia la contraseña desde la app, no se pisa.
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@woowkids.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin1234}"
admin_hash=$(ADMIN_PASSWORD="$ADMIN_PASSWORD" python -c \
    "import os; from app.core.security import hash_password; print(hash_password(os.environ['ADMIN_PASSWORD']))")
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -q \
    -v email="$ADMIN_EMAIL" -v hash="$admin_hash" <<'SQL'
INSERT INTO public.usuarios (email, password_hash, nombre_completo, rol)
SELECT :'email', :'hash', 'Administrador', r.id
FROM public.roles r
WHERE r.nombre = 'AdministradorSistema'
ON CONFLICT (email) DO NOTHING;
SQL
echo "[entrypoint] Administrador inicial: $ADMIN_EMAIL"

exec "$@"
