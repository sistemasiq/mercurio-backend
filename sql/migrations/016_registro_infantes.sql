-- 016_registro_infantes.sql
-- Esquema del módulo registro-infantes (check-in/check-out de niños en estancia).
-- No existe ninguna migración versionada para este módulo en el historial del
-- repo; se infiere de las columnas que asumen app/repositories/{ninos,tutores,
-- registros,detalles_registro,pulseras,pagos,cargos_extra_estancia}.py y los
-- servicios app/services/{estancias,chekouts,pagos_estancia}.py.
-- Revisar contra la BD compartida real si difiere.

CREATE TABLE IF NOT EXISTS public.tutores (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id     UUID         NOT NULL REFERENCES public.sucursales(id),
    nombre_completo VARCHAR(200) NOT NULL,
    telefono        VARCHAR(10)  NOT NULL,

    activo          BOOLEAN     NOT NULL DEFAULT TRUE,
    creado          TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por      UUID        REFERENCES public.usuarios(id),
    modificado      TIMESTAMPTZ DEFAULT now(),
    modificado_por  UUID        REFERENCES public.usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_tutores_telefono_sucursal ON public.tutores (telefono, sucursal_id);

CREATE TABLE IF NOT EXISTS public.ninos (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id     UUID         NOT NULL REFERENCES public.sucursales(id),
    nombre_completo VARCHAR(200) NOT NULL,
    edad            INTEGER      NOT NULL,
    notas           TEXT,

    activo          BOOLEAN     NOT NULL DEFAULT TRUE,
    creado          TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por      UUID        REFERENCES public.usuarios(id),
    modificado      TIMESTAMPTZ DEFAULT now(),
    modificado_por  UUID        REFERENCES public.usuarios(id)
);

CREATE TABLE IF NOT EXISTS public.pulseras (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id     UUID        NOT NULL REFERENCES public.sucursales(id),
    pulsera_rfid    CHAR(10)    NOT NULL,

    activo          BOOLEAN     NOT NULL DEFAULT TRUE,
    creado          TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por      UUID        REFERENCES public.usuarios(id),
    modificado      TIMESTAMPTZ DEFAULT now(),
    modificado_por  UUID        REFERENCES public.usuarios(id),

    CONSTRAINT uq_pulseras_rfid_sucursal UNIQUE (pulsera_rfid, sucursal_id)
);

CREATE TABLE IF NOT EXISTS public.registros (
    id             UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id    UUID           NOT NULL REFERENCES public.sucursales(id),
    tutores_id     UUID           NOT NULL REFERENCES public.tutores(id),
    total          NUMERIC(10, 2) NOT NULL DEFAULT 0,
    estado         VARCHAR(1)     NOT NULL DEFAULT 'P',  -- P pendiente de pago | A activo | C cerrado

    activo         BOOLEAN     NOT NULL DEFAULT TRUE,
    creado         TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por     UUID        REFERENCES public.usuarios(id),
    modificado     TIMESTAMPTZ DEFAULT now(),
    modificado_por UUID        REFERENCES public.usuarios(id)
);

CREATE TABLE IF NOT EXISTS public.fotos (
    id             UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    registro_id    UUID           NOT NULL REFERENCES registros(id),
    tipo           CHAR(1)        NOT NULL,
    storage_url    TEXT           NOT NULL,

    activo         BOOLEAN        DEFAULT TRUE NOT NULL,
    creado         TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    creado_por     UUID,
    modificado     TIMESTAMP WITH TIME ZONE,
    modificado_por UUID,

    CONSTRAINT fotos_tipo_check CHECK (tipo IN ('I', 'L'))
);


CREATE INDEX IF NOT EXISTS idx_registros_sucursal_estado ON public.registros (sucursal_id, estado);

CREATE TABLE IF NOT EXISTS public.detalles_registro (
    id              UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id     UUID           NOT NULL REFERENCES public.sucursales(id),
    registros_id    UUID           NOT NULL REFERENCES public.registros(id),
    ninos_id        UUID           NOT NULL REFERENCES public.ninos(id),
    pulseras_id     UUID           NOT NULL REFERENCES public.pulseras(id),
    productos_id    UUID           NOT NULL REFERENCES public.productos(id),
    cantidad        INTEGER        NOT NULL,
    precio          NUMERIC(10, 2) NOT NULL,
    parentesco      VARCHAR(100)   NOT NULL,
    entrada         TIMESTAMPTZ    NOT NULL,
    salida_esperada TIMESTAMPTZ    NOT NULL,
    salida          TIMESTAMPTZ,

    activo          BOOLEAN     NOT NULL DEFAULT TRUE,
    creado          TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por      UUID        REFERENCES public.usuarios(id),
    modificado      TIMESTAMPTZ DEFAULT now(),
    modificado_por  UUID        REFERENCES public.usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_detalles_registro_sucursal_abiertos
    ON public.detalles_registro (sucursal_id, registros_id) WHERE salida IS NULL;

CREATE TABLE IF NOT EXISTS public.pagos_estancia (
    id              UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id     UUID           NOT NULL REFERENCES public.sucursales(id),
    registros_id    UUID           NOT NULL REFERENCES public.registros(id),
    metodos_pago_id UUID           NOT NULL REFERENCES public.metodos_pago(id),
    monto           NUMERIC(10, 2) NOT NULL,

    creado          TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por      UUID        REFERENCES public.usuarios(id)
);

CREATE TABLE IF NOT EXISTS public.cargos_extra_estancia (
    id                    UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id           UUID           NOT NULL REFERENCES public.sucursales(id),
    registros_id          UUID           NOT NULL REFERENCES public.registros(id),
    detalles_registro_id  UUID           NOT NULL REFERENCES public.detalles_registro(id),
    cantidad              INTEGER        NOT NULL,
    precio                NUMERIC(10, 2) NOT NULL,
    total                 NUMERIC(10, 2) NOT NULL,

    creado                TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por            UUID        REFERENCES public.usuarios(id)
);
