-- 020_corte_caja.sql
-- Módulo de Cierre de Caja: tipos ENUM, tablas, índices y seed de turnos.
-- Convención de nombres: sufijo _id para FKs (sucursal_id, cajero_id, etc.)

-- ─── 1. PIN del cajero en usuarios ───────────────────────────────────────────
ALTER TABLE public.usuarios
    ADD COLUMN IF NOT EXISTS pin_hash CHAR(60);

-- ─── 2. Tipos ENUM (DO block para idempotencia) ───────────────────────────────
DO $$ BEGIN
    CREATE TYPE public.conceptos_retiro AS ENUM (
        'Pago a proveedor',
        'Compra de insumos',
        'Depósito bancario',
        'Resguardo de efectivo',
        'Pago de servicios',
        'Gastos administrativos',
        'Gastos varios'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE public.tipos_destinatario AS ENUM (
        'Proveedor',
        'Empleado',
        'Administrador'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    -- E=estancia  O=orden  R=reservacion
    CREATE TYPE public.tipo_movimiento_caja AS ENUM ('E', 'O', 'R');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE public.tipo_cierre_enum AS ENUM ('NORMAL', 'EXTRAORDINARIO');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ─── 3. Cajas físicas (terminales POS) ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.cajas (
    id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id    UUID         NOT NULL REFERENCES public.sucursales(id),
    codigo         VARCHAR(20)  NOT NULL,
    nombre         VARCHAR(100) NOT NULL,
    creado         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    creado_por     UUID         REFERENCES public.usuarios(id),
    modificado     TIMESTAMPTZ  DEFAULT now(),
    modificado_por UUID         REFERENCES public.usuarios(id),
    CONSTRAINT uq_cajas_codigo_sucursal UNIQUE (codigo, sucursal_id)
);

CREATE INDEX IF NOT EXISTS idx_cajas_sucursal ON public.cajas(sucursal_id);

-- ─── 4. Turnos horarios configurables ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.turnos (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre         VARCHAR(50) NOT NULL UNIQUE,
    hora_inicio    TIME        NOT NULL,
    hora_fin       TIME        NOT NULL,
    creado         TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por     UUID        REFERENCES public.usuarios(id),
    modificado     TIMESTAMPTZ DEFAULT now(),
    modificado_por UUID        REFERENCES public.usuarios(id)
);

-- Seed: turnos por defecto
INSERT INTO public.turnos (nombre, hora_inicio, hora_fin)
VALUES
    ('Turno Matutino',   '08:00:00', '16:00:00'),
    ('Turno Vespertino', '16:00:00', '00:00:00'),
    ('Turno Nocturno',   '00:00:00', '08:00:00')
ON CONFLICT (nombre) DO NOTHING;

-- ─── 5. Apertura de caja (turno operativo) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS public.apertura_caja (
    id               UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    caja_id          UUID           NOT NULL REFERENCES public.cajas(id),
    cajero_id        UUID           NOT NULL REFERENCES public.usuarios(id),
    turno_id         UUID           NOT NULL REFERENCES public.turnos(id),
    fondo_inicial    NUMERIC(12,2)  NOT NULL DEFAULT 0.00,
    estado           VARCHAR(20)    NOT NULL DEFAULT 'ABIERTA',
    -- ABIERTA | EN_CORTE | CERRADA

    -- Datos del conteo físico (guardados al enviar el conteo)
    conteo_json      TEXT,          -- payload completo del cajero (JSON serializado)
    monto_declarado  NUMERIC(12,2), -- total declarado por el cajero

    -- Token temporal del admin (JTI del JWT de un solo uso)
    token_admin_jti  UUID,

    creado           TIMESTAMPTZ    NOT NULL DEFAULT now(),
    creado_por       UUID           REFERENCES public.usuarios(id),
    modificado       TIMESTAMPTZ    DEFAULT now(),
    modificado_por   UUID           REFERENCES public.usuarios(id),

    CONSTRAINT chk_apertura_estado    CHECK (estado IN ('ABIERTA','EN_CORTE','CERRADA')),
    CONSTRAINT chk_fondo_no_negativo  CHECK (fondo_inicial >= 0)
);

-- RN-APE-001: un cajero solo puede tener UN turno activo a la vez
CREATE UNIQUE INDEX IF NOT EXISTS uq_apertura_cajero_activo
    ON public.apertura_caja(cajero_id) WHERE estado != 'CERRADA';

-- RN-APE-002: una caja solo puede tener UN turno activo a la vez
CREATE UNIQUE INDEX IF NOT EXISTS uq_apertura_caja_activa
    ON public.apertura_caja(caja_id) WHERE estado != 'CERRADA';

CREATE INDEX IF NOT EXISTS idx_apertura_cajero ON public.apertura_caja(cajero_id);

-- ─── 6. Movimientos de caja (libro mayor del turno — INMUTABLE) ───────────────
CREATE TABLE IF NOT EXISTS public.movimientos_caja (
    id               BIGSERIAL                   PRIMARY KEY,
    apertura_caja_id UUID                        NOT NULL REFERENCES public.apertura_caja(id),
    tipo_movimiento  public.tipo_movimiento_caja  NOT NULL,
    referencia_id    UUID                        NOT NULL,
    metodo_pago_id   UUID                        NOT NULL REFERENCES public.metodos_pago(id),
    monto            NUMERIC(12,2)               NOT NULL CHECK (monto > 0),
    creado           TIMESTAMPTZ                 NOT NULL DEFAULT now(),
    creado_por       UUID                        REFERENCES public.usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_movimientos_apertura
    ON public.movimientos_caja(apertura_caja_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_apertura_metodo
    ON public.movimientos_caja(apertura_caja_id, metodo_pago_id);

-- ─── 7. Retiros parciales (INMUTABLE) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.retiros_parciales (
    id               BIGSERIAL                   PRIMARY KEY,
    apertura_caja_id UUID                        NOT NULL REFERENCES public.apertura_caja(id),
    concepto         public.conceptos_retiro     NOT NULL,
    tipo_destinatario public.tipos_destinatario  NOT NULL,
    monto            NUMERIC(12,2)               NOT NULL CHECK (monto > 0),
    observaciones    TEXT,
    creado           TIMESTAMPTZ                 NOT NULL DEFAULT now(),
    creado_por       UUID                        REFERENCES public.usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_retiros_apertura
    ON public.retiros_parciales(apertura_caja_id);

-- ─── 8. Cierre de caja (registro final del arqueo — INMUTABLE) ───────────────
CREATE TABLE IF NOT EXISTS public.cierre_caja (
    id                        UUID                    PRIMARY KEY DEFAULT gen_random_uuid(),
    apertura_caja_id          UUID                    NOT NULL UNIQUE REFERENCES public.apertura_caja(id),
    tipo_cierre               public.tipo_cierre_enum NOT NULL DEFAULT 'NORMAL',
    monto_sistema             NUMERIC(12,2)           NOT NULL,  -- calculado por el sistema
    monto_cierre              NUMERIC(12,2)           NOT NULL,  -- declarado por el cajero
    cajero_id                 UUID                    REFERENCES public.usuarios(id),
    fecha_autorizacion_cajero TIMESTAMPTZ,
    administrador_id          UUID                    NOT NULL REFERENCES public.usuarios(id),
    fecha_autorizacion_admin  TIMESTAMPTZ             NOT NULL DEFAULT now(),
    observaciones             TEXT,
    creado                    TIMESTAMPTZ             NOT NULL DEFAULT now(),
    creado_por                UUID                    REFERENCES public.usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_cierre_apertura ON public.cierre_caja(apertura_caja_id);
