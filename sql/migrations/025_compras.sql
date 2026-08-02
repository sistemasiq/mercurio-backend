-- =============================================================================
-- 025_compras.sql
-- Fase 4 de inventario: orden de compra a proveedor (entrada formal de stock).
-- unidad_medida_id en detalle_compras es la unidad en la que el proveedor
-- facturó esa línea; la conversión a insumos.unidad_base_id ocurre solo al
-- recibir la compra (ver INVENTARIO_DISENO.md §3.2.1).
-- =============================================================================

CREATE TABLE public.compras (
    id              UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id     UUID           NOT NULL REFERENCES public.sucursales(id),
    proveedor_id    UUID           NOT NULL REFERENCES public.proveedores(id),
    estado          VARCHAR(1)     NOT NULL DEFAULT 'P',  -- P'endiente | R'ecibida | C'ancelada
    fecha_pedido    TIMESTAMPTZ    NOT NULL DEFAULT now(),
    fecha_recepcion TIMESTAMPTZ,
    total           NUMERIC(10, 2) NOT NULL DEFAULT 0,
    notas           TEXT,

    activo          BOOLEAN     NOT NULL DEFAULT TRUE,
    creado          TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por      UUID        REFERENCES public.usuarios(id),
    modificado      TIMESTAMPTZ DEFAULT now(),
    modificado_por  UUID        REFERENCES public.usuarios(id)
);

CREATE INDEX idx_compras_sucursal_estado ON public.compras (sucursal_id, estado);

CREATE TABLE public.detalle_compras (
    id               UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    compra_id        UUID           NOT NULL REFERENCES public.compras(id),
    insumo_id        UUID           NOT NULL REFERENCES public.insumos(id),
    unidad_medida_id UUID           NOT NULL REFERENCES public.unidades_medida(id),
    cantidad         NUMERIC(12, 3) NOT NULL CHECK (cantidad > 0),
    costo_unitario   NUMERIC(10, 2) NOT NULL CHECK (costo_unitario >= 0),
    subtotal         NUMERIC(10, 2) GENERATED ALWAYS AS (cantidad * costo_unitario) STORED
);

CREATE INDEX idx_detalle_compras_compra ON public.detalle_compras (compra_id);
