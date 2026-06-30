-- 003_reservaciones.sql
-- Reservaciones de eventos, extras seleccionados y pagos registrados.
-- saldo_pendiente y subtotal son columnas generadas (persistidas).

CREATE TABLE IF NOT EXISTS public.reservaciones (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id           UUID NOT NULL REFERENCES public.sucursales(id),
    tipo_evento_id        UUID NOT NULL REFERENCES public.tipos_evento(id),
    paquete_id            UUID NOT NULL REFERENCES public.paquetes(id),

    -- Cliente
    nombre_cliente        VARCHAR(150) NOT NULL,
    apellidos_cliente     VARCHAR(150),
    telefono_cliente      VARCHAR(10) NOT NULL,
    email_cliente         VARCHAR(150),
    notas_cliente         TEXT,

    -- Festejado
    nombre_festejado      VARCHAR(150),
    edad_festejado        INTEGER,

    -- Fecha y horario
    fecha_evento          DATE NOT NULL,
    hora_inicio           TIME NOT NULL,
    hora_fin              TIME NOT NULL,

    -- Precios
    numero_personas       INTEGER NOT NULL,
    precio_base           NUMERIC(10, 2) NOT NULL,
    precio_personas_extra NUMERIC(10, 2) NOT NULL DEFAULT 0,
    precio_extras         NUMERIC(10, 2) NOT NULL DEFAULT 0,
    descuento             NUMERIC(10, 2) NOT NULL DEFAULT 0,
    precio_total          NUMERIC(10, 2) NOT NULL,
    anticipo              NUMERIC(10, 2) NOT NULL DEFAULT 0,
    saldo_pendiente       NUMERIC(10, 2) GENERATED ALWAYS AS (precio_total - anticipo) STORED,

    -- Estado y auditoría
    estado                VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    notas                 TEXT,
    activo                BOOLEAN NOT NULL DEFAULT TRUE,
    creado                TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por            UUID,
    modificado            TIMESTAMPTZ DEFAULT now(),
    modificado_por        UUID
);

CREATE TABLE IF NOT EXISTS public.reservacion_extras (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reservacion_id  UUID NOT NULL REFERENCES public.reservaciones(id),
    extra_id        UUID NOT NULL REFERENCES public.extras(id),
    cantidad        INTEGER NOT NULL,
    precio_unitario NUMERIC(10, 2) NOT NULL,
    subtotal        NUMERIC(10, 2) GENERATED ALWAYS AS (cantidad * precio_unitario) STORED,
    creado          TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por      UUID
);

CREATE TABLE IF NOT EXISTS public.pagos_reservacion (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reservacion_id UUID NOT NULL REFERENCES public.reservaciones(id),
    metodo_pago_id UUID NOT NULL REFERENCES public.metodos_pago(id),
    monto          NUMERIC(10, 2) NOT NULL,
    fecha_pago     TIMESTAMPTZ NOT NULL DEFAULT now(),
    notas          VARCHAR(255),
    creado_por     UUID
);
