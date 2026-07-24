-- =============================================================================
-- 019_inventario_catalogos.sql
-- Fase 1 del módulo de inventario: catálogos base.
-- unidades_medida: catálogo global sembrado (sin CRUD desde la UI), con factor
-- de conversión a la unidad base de su tipo (masa -> gramo, volumen -> mililitro,
-- pieza -> pieza). proveedores e insumos son por sucursal, como el resto del
-- sistema.
-- =============================================================================

CREATE TABLE public.unidades_medida (
    id             UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo         VARCHAR(10)   NOT NULL UNIQUE,
    nombre         VARCHAR(50)   NOT NULL,
    tipo           VARCHAR(20)   NOT NULL,  -- 'masa' | 'volumen' | 'pieza'
    factor_a_base  NUMERIC(14, 6) NOT NULL,
    activo         BOOLEAN       NOT NULL DEFAULT TRUE
);

INSERT INTO public.unidades_medida (codigo, nombre, tipo, factor_a_base) VALUES
    ('g',   'Gramo',     'masa',    1),
    ('kg',  'Kilogramo', 'masa',    1000),
    ('ml',  'Mililitro', 'volumen', 1),
    ('l',   'Litro',     'volumen', 1000),
    ('pza', 'Pieza',     'pieza',   1);

CREATE TABLE public.proveedores (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id     UUID         NOT NULL REFERENCES public.sucursales(id),
    nombre          VARCHAR(150) NOT NULL,
    contacto_nombre VARCHAR(150),
    telefono        VARCHAR(20),
    email           VARCHAR(150),
    notas           TEXT,

    activo          BOOLEAN     NOT NULL DEFAULT TRUE,
    creado          TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por      UUID        REFERENCES public.usuarios(id),
    modificado      TIMESTAMPTZ DEFAULT now(),
    modificado_por  UUID        REFERENCES public.usuarios(id)
);

CREATE INDEX idx_proveedores_sucursal ON public.proveedores (sucursal_id);

CREATE TABLE public.insumos (
    id                     UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id            UUID           NOT NULL REFERENCES public.sucursales(id),
    nombre                 VARCHAR(150)   NOT NULL,
    descripcion            TEXT,
    unidad_base_id         UUID           NOT NULL REFERENCES public.unidades_medida(id),
    unidad_compra_id       UUID           NOT NULL REFERENCES public.unidades_medida(id),
    stock_actual           NUMERIC(12, 3) NOT NULL DEFAULT 0,
    stock_minimo           NUMERIC(12, 3) NOT NULL DEFAULT 0,
    costo_unitario         NUMERIC(10, 2),
    proveedor_principal_id UUID           REFERENCES public.proveedores(id),

    activo                 BOOLEAN     NOT NULL DEFAULT TRUE,
    creado                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por             UUID        REFERENCES public.usuarios(id),
    modificado             TIMESTAMPTZ DEFAULT now(),
    modificado_por         UUID        REFERENCES public.usuarios(id)
);

CREATE INDEX idx_insumos_sucursal ON public.insumos (sucursal_id);
