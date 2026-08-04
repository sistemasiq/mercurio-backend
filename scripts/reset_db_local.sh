#!/usr/bin/env bash
# Reconstruye la BD local desde cero aplicando todas las migraciones en orden.
#
# Es idempotente por fuerza bruta: tira el esquema public completo y lo vuelve
# a levantar, así que siempre refleja exactamente lo que producen los archivos
# de sql/migrations/ — que es justo lo que se quiere validar antes de tocar la
# BD compartida.
#
# Uso:  ./scripts/reset_db_local.sh [--seed]
set -euo pipefail

cd "$(dirname "$0")/.."

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5433}"
DB_USER="${DB_USER:-dev}"
DB_NAME="${DB_NAME:-mercury}"
export PGPASSWORD="${PGPASSWORD:-dev}"

psql_run() { psql -v ON_ERROR_STOP=1 -q -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" "$@"; }

echo "==> Limpiando esquema public en $DB_HOST:$DB_PORT/$DB_NAME"
psql_run -c 'DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;'

echo "==> Aplicando migraciones"
# `sort` da un orden estable y determinista; hay números repetidos (019_a,
# 019_b...) y el desempate alfabético es el mismo que se usó al crearlos.
for f in $(find sql/migrations -name '*.sql' | sort); do
    printf '    %-60s' "$(basename "$f")"
    if psql_run -f "$f" > /tmp/mig_out.txt 2>&1; then
        echo 'ok'
    else
        echo 'FALLÓ'
        cat /tmp/mig_out.txt
        exit 1
    fi
done

if [[ "${1:-}" == "--seed" ]]; then
    echo "==> Sembrando datos de prueba"
    psql_run -f sql/seed_local.sql
fi

echo "==> Listo"
