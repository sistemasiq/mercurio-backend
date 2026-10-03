#!/usr/bin/env bash
# Genera sql/schema_maestro.sql: un solo archivo que crea la BD completa
# (esquema + datos de catálogo que insertan las migraciones: roles, permisos,
# métodos de pago, unidades de medida, ...).
#
# NO se escribe a mano: se obtiene aplicando TODAS las migraciones de
# sql/migrations/ sobre un PostgreSQL desechable en Docker y volcando el
# resultado. Así el maestro es, por construcción, idéntico a lo que producen
# las migraciones. Después lo valida cargándolo en otra BD limpia y
# comparando ambos esquemas.
#
# Las migraciones se conservan: siguen siendo el historial y la forma de
# actualizar una BD existente. El maestro sirve para levantar una BD nueva.
#
# Uso:  ./scripts/generar_schema_maestro.sh
# Requiere: docker. Regenerarlo cada vez que se agregue una migración.
set -euo pipefail

cd "$(dirname "$0")/.."

# Versión fija: el CI regenera el maestro y debe salir idéntico al versionado.
IMAGEN="${PG_IMAGEN:-postgres:16.14-alpine}"
CONTENEDOR="woowkids-schema-gen-$$"
SALIDA="sql/schema_maestro.sql"
TMP="$(mktemp -d)"

limpiar() {
    docker rm -f "$CONTENEDOR" >/dev/null 2>&1 || true
    rm -rf "$TMP"
}
trap limpiar EXIT

pg() { docker exec -i "$CONTENEDOR" psql -v ON_ERROR_STOP=1 -q -U dev "$@"; }

sin_restrict() { grep -vE '^\\(un)?restrict ' || true; }

# Consulta sin -i: dentro de un `while read` un docker exec interactivo se come
# el stdin del ciclo (las líneas que faltan por leer).
pgq() { docker exec "$CONTENEDOR" psql -v ON_ERROR_STOP=1 -q -At -U dev -d mercury -c "$1"; }

# Normaliza un volcado para compararlo: quita los tokens de \restrict y, en las
# líneas CHECK, los casts y paréntesis que PostgreSQL re-escribe distinto al
# reconstruir la restricción desde el volcado (mismo significado, otro texto).
normalizar() {
    sin_restrict | sed -E '/CHECK/{s/::(character varying|text)//g; s/[()]//g; s/\[\]//g}'
}

echo "==> Levantando PostgreSQL desechable ($IMAGEN)"
docker run -d --name "$CONTENEDOR" \
    -e POSTGRES_USER=dev -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=mercury \
    -v "$PWD/sql/migrations:/migrations:ro" \
    "$IMAGEN" >/dev/null
until docker exec "$CONTENEDOR" pg_isready -U dev -d mercury >/dev/null 2>&1; do sleep 1; done
# pg_isready responde antes de que termine el arranque inicial: se espera a que
# la BD acepte una consulta real.
until pg -d mercury -c 'SELECT 1' >/dev/null 2>&1; do sleep 1; done

echo "==> Aplicando migraciones"
# Mismo orden que scripts/reset_db_local.sh (`sort` estable; hay números
# repetidos como 019_a / 019_b y el desempate alfabético es el original).
total=0
for f in $(find sql/migrations -name '*.sql' | sort); do
    nombre="$(basename "$f")"
    if ! pg -d mercury -f "/migrations/$nombre" >"$TMP/mig.log" 2>&1; then
        echo "    FALLÓ: $nombre"
        cat "$TMP/mig.log"
        exit 1
    fi
    total=$((total + 1))
done
echo "    $total migraciones aplicadas"

echo "==> Volcando esquema"
docker exec "$CONTENEDOR" pg_dump -U dev -d mercury \
    --schema-only --no-owner --no-privileges --no-comments \
    >"$TMP/schema.sql"

echo "==> Volcando datos de catálogo (tablas que las migraciones dejan con filas)"
tablas=$(pgq "
    SELECT format('%I.%I', schemaname, relname)
    FROM pg_stat_user_tables
    ORDER BY schemaname, relname" | while read -r t; do
        n=$(pgq "SELECT count(*) FROM $t")
        if [ "$n" -gt 0 ]; then echo "$t"; fi
    done)
args=()
for t in $tablas; do args+=(--table="$t"); done
if [ ${#args[@]} -gt 0 ]; then
    # --column-inserts: legible y resistente a reordenar columnas.
    # --disable-triggers no hace falta: se carga después del esquema completo y
    # pg_dump ordena las tablas respetando las llaves foráneas.
    docker exec "$CONTENEDOR" pg_dump -U dev -d mercury \
        --data-only --column-inserts --no-owner --no-privileges "${args[@]}" \
        >"$TMP/datos.sql"
else
    : >"$TMP/datos.sql"
fi
echo "    Tablas con datos: $(echo "$tablas" | grep -c . || true)"

ultima="$(find sql/migrations -name '*.sql' | sort | tail -1 | xargs basename)"
{
    echo "-- ============================================================================="
    echo "-- schema_maestro.sql — Crea la base de datos completa de Woow Kids en un paso."
    echo "--"
    echo "-- GENERADO por scripts/generar_schema_maestro.sh. NO editar a mano: agrega una"
    echo "-- migración en sql/migrations/ y vuelve a correr el script."
    echo "--"
    echo "-- Equivale a aplicar las $total migraciones de sql/migrations/ en orden"
    echo "-- (última: $ultima)."
    echo "-- Incluye el esquema y los datos de catálogo que esas migraciones insertan"
    echo "-- (roles, permisos, etc.). No incluye datos de prueba: para eso está"
    echo "-- sql/seed_local.sql."
    echo "--"
    echo "-- Uso, sobre una BD VACÍA:"
    echo "--   psql -v ON_ERROR_STOP=1 -h <host> -U <usuario> -d <bd> -f sql/schema_maestro.sql"
    echo "-- ============================================================================="
    echo
    # \restrict / \unrestrict (pg_dump >= 16.10) llevan un token aleatorio por
    # volcado y psql anteriores no los reconocen: el maestro es un archivo de
    # confianza versionado, así que se omiten para que cargue con cualquier psql.
    echo "-- ---------------------------------------------------------------- Esquema"
    sin_restrict <"$TMP/schema.sql"
    echo
    echo "-- ------------------------------------------------------ Datos de catálogo"
    sin_restrict <"$TMP/datos.sql"
} >"$SALIDA"

echo "==> Validando: cargando el maestro en una BD limpia"
pg -d mercury -c 'CREATE DATABASE mercury_check' >/dev/null
docker cp "$SALIDA" "$CONTENEDOR:/tmp/maestro.sql"
pg -d mercury_check -f /tmp/maestro.sql >"$TMP/carga.log" 2>&1 || {
    echo "    El maestro NO carga en una BD limpia:"
    tail -20 "$TMP/carga.log"
    exit 1
}
for bd in mercury mercury_check; do
    docker exec "$CONTENEDOR" pg_dump -U dev -d "$bd" \
        --schema-only --no-owner --no-privileges --no-comments >"$TMP/$bd.schema"
    docker exec "$CONTENEDOR" pg_dump -U dev -d "$bd" \
        --data-only --column-inserts --no-owner --no-privileges "${args[@]}" >"$TMP/$bd.datos"
done
for f in mercury.schema mercury_check.schema mercury.datos mercury_check.datos; do
    normalizar <"$TMP/$f" >"$TMP/$f.norm"
done
if diff -q "$TMP/mercury.schema.norm" "$TMP/mercury_check.schema.norm" >/dev/null &&
    diff -q "$TMP/mercury.datos.norm" "$TMP/mercury_check.datos.norm" >/dev/null; then
    echo "    OK: el maestro produce exactamente el mismo esquema y datos que las migraciones"
else
    echo "    DIFERENCIAS entre migraciones y maestro:"
    diff "$TMP/mercury.schema.norm" "$TMP/mercury_check.schema.norm" | head -40 || true
    diff "$TMP/mercury.datos.norm" "$TMP/mercury_check.datos.norm" | head -40 || true
    exit 1
fi

echo "==> Listo: $SALIDA ($(wc -l <"$SALIDA") líneas)"
