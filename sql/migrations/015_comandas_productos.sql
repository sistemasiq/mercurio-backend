-- 015_comandas_productos.sql
-- Esquema del módulo comandas (productos, comandas, detalles_comanda).
-- No existe ninguna migración versionada para este módulo en el historial del
-- repo (ni en integration/develop ni en ninguna feature branch); se infiere de
-- las columnas que asumen app/repositories/producto_repository.py, productos.py
-- y comanda_repository.py. Revisar contra la BD compartida real si difiere.

CREATE TABLE IF NOT EXISTS public.productos (
    id              UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre          VARCHAR(150)   NOT NULL,
    precio_unitario NUMERIC(10, 2) NOT NULL,
    tipo            VARCHAR(1)     NOT NULL,  -- 'A' alimento | 'B' bebida | 'E' estancia | 'S' servicio
    sucursal_id     UUID           NOT NULL REFERENCES public.sucursales(id),
    descripcion     TEXT,
    imagen          TEXT,

    activo          BOOLEAN     NOT NULL DEFAULT TRUE,
    creado          TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por      UUID        REFERENCES public.usuarios(id),
    modificado      TIMESTAMPTZ DEFAULT now(),
    modificado_por  UUID        REFERENCES public.usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_productos_sucursal ON public.productos (sucursal_id);

CREATE TABLE IF NOT EXISTS public.comandas (
    id             UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_numero  VARCHAR(50)    NOT NULL,
    estado_actual  VARCHAR(1)     NOT NULL DEFAULT 'P',  -- P|E|L|T|C (ver EstadoComanda)
    total_final    NUMERIC(10, 2) NOT NULL,
    sucursal_id    UUID           NOT NULL REFERENCES public.sucursales(id),
    fecha_hora     TIMESTAMPTZ    NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_comandas_sucursal_estado ON public.comandas (sucursal_id, estado_actual);

CREATE TABLE IF NOT EXISTS public.detalles_comanda (
    id                UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    comanda_id        UUID           NOT NULL REFERENCES public.comandas(id) ON DELETE CASCADE,
    producto_id       UUID           NOT NULL REFERENCES public.productos(id),
    cantidad          INTEGER        NOT NULL,
    precio_unitario   NUMERIC(10, 2) NOT NULL,
    importe           NUMERIC(10, 2) NOT NULL,
    sucursal_id       UUID           NOT NULL REFERENCES public.sucursales(id),
    notas_especiales  TEXT
);

CREATE INDEX IF NOT EXISTS idx_detalles_comanda_comanda ON public.detalles_comanda (comanda_id);
