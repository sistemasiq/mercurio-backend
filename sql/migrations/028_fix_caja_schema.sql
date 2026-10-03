-- 028_fix_caja_schema.sql
-- Corrige el drift de esquema entre feature/cierre-caja-backend (convención id_*)
-- y el refactor en feat/corte-caja (convención *_id).
-- Las tablas fueron creadas con el nombre de columnas antiguo; este script las
-- recrea con la estructura que espera el repositorio actual.
-- Seguro en desarrollo: no hay datos productivos en estas tablas aún.

-- ── Borrar en orden inverso de dependencias ───────────────────────────────────
DROP TABLE IF EXISTS public.cierre_caja       CASCADE;
DROP TABLE IF EXISTS public.movimientos_caja  CASCADE;
DROP TABLE IF EXISTS public.retiros_parciales CASCADE;
DROP TABLE IF EXISTS public.apertura_caja     CASCADE;
DROP TABLE IF EXISTS public.cajas             CASCADE;
DROP TABLE IF EXISTS public.turnos            CASCADE;

-- ── Recrear con la convención correcta (*_id) ─────────────────────────────────

-- Cajas físicas (terminales POS)
CREATE TABLE public.cajas (
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

CREATE INDEX idx_cajas_sucursal ON public.cajas(sucursal_id);

-- Turnos horarios configurables
CREATE TABLE public.turnos (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre         VARCHAR(50) NOT NULL UNIQUE,
    hora_inicio    TIME        NOT NULL,
    hora_fin       TIME        NOT NULL,
    creado         TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por     UUID        REFERENCES public.usuarios(id),
    modificado     TIMESTAMPTZ DEFAULT now(),
    modificado_por UUID        REFERENCES public.usuarios(id)
);

INSERT INTO public.turnos (nombre, hora_inicio, hora_fin)
VALUES
    ('Turno Matutino',   '08:00:00', '16:00:00'),
    ('Turno Vespertino', '16:00:00', '00:00:00'),
    ('Turno Nocturno',   '00:00:00', '08:00:00')
ON CONFLICT (nombre) DO NOTHING;

-- Apertura de caja (turno operativo)
CREATE TABLE public.apertura_caja (
    id               UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    caja_id          UUID           NOT NULL REFERENCES public.cajas(id),
    cajero_id        UUID           NOT NULL REFERENCES public.usuarios(id),
    turno_id         UUID           NOT NULL REFERENCES public.turnos(id),
    fondo_inicial    NUMERIC(12,2)  NOT NULL DEFAULT 0.00,
    estado           VARCHAR(20)    NOT NULL DEFAULT 'ABIERTA',
    conteo_json      TEXT,
    monto_declarado  NUMERIC(12,2),
    token_admin_jti  UUID,
    creado           TIMESTAMPTZ    NOT NULL DEFAULT now(),
    creado_por       UUID           REFERENCES public.usuarios(id),
    modificado       TIMESTAMPTZ    DEFAULT now(),
    modificado_por   UUID           REFERENCES public.usuarios(id),
    CONSTRAINT chk_apertura_estado   CHECK (estado IN ('ABIERTA','EN_CORTE','CERRADA')),
    CONSTRAINT chk_fondo_no_negativo CHECK (fondo_inicial >= 0)
);

CREATE UNIQUE INDEX uq_apertura_cajero_activo
    ON public.apertura_caja(cajero_id) WHERE estado != 'CERRADA';

CREATE UNIQUE INDEX uq_apertura_caja_activa
    ON public.apertura_caja(caja_id) WHERE estado != 'CERRADA';

CREATE INDEX idx_apertura_cajero ON public.apertura_caja(cajero_id);

-- Movimientos de caja (libro mayor del turno — INMUTABLE)
CREATE TABLE public.movimientos_caja (
    id               BIGSERIAL                   PRIMARY KEY,
    apertura_caja_id UUID                        NOT NULL REFERENCES public.apertura_caja(id),
    tipo_movimiento  public.tipo_movimiento_caja  NOT NULL,
    referencia_id    UUID                        NOT NULL,
    metodo_pago_id   UUID                        NOT NULL REFERENCES public.metodos_pago(id),
    monto            NUMERIC(12,2)               NOT NULL CHECK (monto > 0),
    creado           TIMESTAMPTZ                 NOT NULL DEFAULT now(),
    creado_por       UUID                        REFERENCES public.usuarios(id)
);

CREATE INDEX idx_movimientos_apertura
    ON public.movimientos_caja(apertura_caja_id);
CREATE INDEX idx_movimientos_apertura_metodo
    ON public.movimientos_caja(apertura_caja_id, metodo_pago_id);

-- Retiros parciales (INMUTABLE)
CREATE TABLE public.retiros_parciales (
    id               BIGSERIAL                   PRIMARY KEY,
    apertura_caja_id UUID                        NOT NULL REFERENCES public.apertura_caja(id),
    concepto         public.conceptos_retiro     NOT NULL,
    tipo_destinatario public.tipos_destinatario  NOT NULL,
    monto            NUMERIC(12,2)               NOT NULL CHECK (monto > 0),
    observaciones    TEXT,
    creado           TIMESTAMPTZ                 NOT NULL DEFAULT now(),
    creado_por       UUID                        REFERENCES public.usuarios(id)
);

CREATE INDEX idx_retiros_apertura
    ON public.retiros_parciales(apertura_caja_id);

-- Cierre de caja (registro final del arqueo — INMUTABLE)
CREATE TABLE public.cierre_caja (
    id                        UUID                    PRIMARY KEY DEFAULT gen_random_uuid(),
    apertura_caja_id          UUID                    NOT NULL UNIQUE REFERENCES public.apertura_caja(id),
    tipo_cierre               public.tipo_cierre_enum NOT NULL DEFAULT 'NORMAL',
    monto_sistema             NUMERIC(12,2)           NOT NULL,
    monto_cierre              NUMERIC(12,2)           NOT NULL,
    cajero_id                 UUID                    REFERENCES public.usuarios(id),
    fecha_autorizacion_cajero TIMESTAMPTZ,
    administrador_id          UUID                    NOT NULL REFERENCES public.usuarios(id),
    fecha_autorizacion_admin  TIMESTAMPTZ             NOT NULL DEFAULT now(),
    observaciones             TEXT,
    creado                    TIMESTAMPTZ             NOT NULL DEFAULT now(),
    creado_por                UUID                    REFERENCES public.usuarios(id)
);

CREATE INDEX idx_cierre_apertura ON public.cierre_caja(apertura_caja_id);
