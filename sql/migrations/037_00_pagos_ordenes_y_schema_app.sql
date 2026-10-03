-- =============================================================================
-- 037_00_pagos_ordenes_y_schema_app.sql
--
-- Rellena objetos que EXISTÍAN solo en la BD compartida de desarrollo (se
-- crearon a mano en su momento, nunca se versionaron) y que migraciones
-- posteriores dan por hechos. Sin esto, reconstruir la BD desde cero con
-- scripts/reset_db_local.sh se rompe en 037_metodos_pago_globales.sql.
--
-- Lo que faltaba:
--   1. Extensión pgcrypto (la BD compartida la tiene; ninguna migración la
--      declaraba).
--   2. Schema `app` + funciones de contexto de sesión. 037 crea políticas RLS
--      y un trigger sobre sucursal_metodos_pago que llaman a
--      app.usuario_tiene_rol / app.usuario_en_sucursal / app.set_modificado.
--      NOTA: la app se conecta como superusuario y NUNCA setea app.rol /
--      app.sucursal_id / app.user_id, así que estas funciones y cualquier RLS
--      que dependa de ellas hoy no filtran nada -- se replican solo para que
--      037 corra y para que una copia local sea idéntica a la compartida. El
--      RLS "durmiente" que la BD compartida tiene sobre extras / sucursales /
--      reservaciones / paquetes / tipos_evento / metodos_pago NO se replica
--      aquí a propósito (no lo necesita ninguna migración y no cambia el
--      comportamiento con el usuario actual).
--   3. Tabla pagos_ordenes: los pagos de comandas del POS. La usa
--      app/repositories/pago_repository.py (INSERT + el historial unificado) y
--      la remapea 037. Nunca tuvo un CREATE TABLE en las migraciones.
--
-- Todo idempotente (IF NOT EXISTS / CREATE OR REPLACE): no-op contra la BD
-- compartida, que ya tiene los tres bloques.
-- =============================================================================

-- 1. pgcrypto ----------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2. Schema app + funciones de contexto -------------------------------------
CREATE SCHEMA IF NOT EXISTS app;

CREATE OR REPLACE FUNCTION app.get_rol()
    RETURNS text LANGUAGE sql STABLE
    AS $$ SELECT current_setting('app.rol', true); $$;

CREATE OR REPLACE FUNCTION app.get_sucursal_id()
    RETURNS uuid LANGUAGE sql STABLE
    AS $$ SELECT NULLIF(current_setting('app.sucursal_id', true), '')::UUID; $$;

CREATE OR REPLACE FUNCTION app.set_modificado()
    RETURNS trigger LANGUAGE plpgsql
    AS $$
    BEGIN
        NEW.modificado     := NOW();
        NEW.modificado_por := NULLIF(current_setting('app.user_id', true), '')::UUID;
        RETURN NEW;
    END;
    $$;

CREATE OR REPLACE FUNCTION app.usuario_en_sucursal(p_sucursal_id uuid)
    RETURNS boolean LANGUAGE sql STABLE
    AS $$
        SELECT app.get_rol() = 'admin'
            OR app.get_sucursal_id() = p_sucursal_id;
    $$;

CREATE OR REPLACE FUNCTION app.usuario_tiene_rol(p_roles text[])
    RETURNS boolean LANGUAGE sql STABLE
    AS $$ SELECT app.get_rol() = ANY(p_roles); $$;

-- 3. pagos_ordenes ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pagos_ordenes (
    id             UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    comanda_id     UUID           NOT NULL,
    metodo_pago_id UUID           NOT NULL,
    monto          NUMERIC(12, 2) NOT NULL CHECK (monto >= 0.00),
    notas_pago     TEXT,
    sucursal_id    UUID           NOT NULL,
    activo         BOOLEAN        NOT NULL DEFAULT TRUE,
    creado         TIMESTAMPTZ    NOT NULL DEFAULT now(),
    creado_por     UUID,
    modificado     TIMESTAMPTZ,
    modificado_por UUID,
    CONSTRAINT fk_pagos_comanda FOREIGN KEY (comanda_id)
        REFERENCES public.comandas(id) ON DELETE CASCADE,
    CONSTRAINT fk_pagos_metodo FOREIGN KEY (metodo_pago_id)
        REFERENCES public.metodos_pago(id) ON DELETE RESTRICT
);
