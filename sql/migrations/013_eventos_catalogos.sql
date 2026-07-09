-- 013_eventos_catalogos.sql (recuperado de origin/feature/eventos, nunca integrado a esta línea)
-- Catálogos del módulo eventos: tipos de evento, métodos de pago, extras,
-- paquetes y la relación paquete <-> tipo de evento.

CREATE TABLE IF NOT EXISTS public.tipos_evento (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre         VARCHAR(100) NOT NULL UNIQUE,
    descripcion    TEXT,
    activo         BOOLEAN NOT NULL DEFAULT TRUE,
    creado         TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por     UUID,
    modificado     TIMESTAMPTZ DEFAULT now(),
    modificado_por UUID
);

CREATE TABLE IF NOT EXISTS public.metodos_pago (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre         VARCHAR(100) NOT NULL UNIQUE,
    descripcion    TEXT,
    activo         BOOLEAN NOT NULL DEFAULT TRUE,
    creado         TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por     UUID,
    modificado     TIMESTAMPTZ DEFAULT now(),
    modificado_por UUID
);

CREATE TABLE IF NOT EXISTS public.extras (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id    UUID REFERENCES public.sucursales(id),  -- NULL = extra global
    nombre         VARCHAR(150) NOT NULL,
    descripcion    TEXT,
    precio         NUMERIC(10, 2) NOT NULL,
    unidad         VARCHAR(50) NOT NULL DEFAULT 'evento',   -- evento | persona | hora
    activo         BOOLEAN NOT NULL DEFAULT TRUE,
    creado         TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por     UUID,
    modificado     TIMESTAMPTZ DEFAULT now(),
    modificado_por UUID
);

CREATE TABLE IF NOT EXISTS public.paquetes (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id          UUID NOT NULL REFERENCES public.sucursales(id),
    nombre               VARCHAR(150) NOT NULL,
    descripcion          TEXT,
    duracion_minutos     INTEGER NOT NULL DEFAULT 120,
    personas_incluidas   INTEGER NOT NULL DEFAULT 10,
    precio_base          NUMERIC(10, 2) NOT NULL,
    precio_persona_extra NUMERIC(10, 2) NOT NULL DEFAULT 0,
    activo               BOOLEAN NOT NULL DEFAULT TRUE,
    creado               TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por           UUID,
    modificado           TIMESTAMPTZ DEFAULT now(),
    modificado_por       UUID
);

CREATE TABLE IF NOT EXISTS public.paquete_tipos_evento (
    paquete_id     UUID NOT NULL REFERENCES public.paquetes(id),
    tipo_evento_id UUID NOT NULL REFERENCES public.tipos_evento(id),
    PRIMARY KEY (paquete_id, tipo_evento_id)
);
