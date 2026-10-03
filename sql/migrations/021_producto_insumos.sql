-- =============================================================================
-- 021_producto_insumos.sql
-- Fase 2 de inventario: receta (BOM) de cada producto — qué insumos y en qué
-- cantidad consume una unidad de un producto del catálogo de venta.
-- Tabla puente pura (sin auditoría), mismo criterio que paquete_tipos_evento.
-- cantidad se expresa siempre en insumos.unidad_base_id del insumo referenciado.
-- =============================================================================

CREATE TABLE public.producto_insumos (
    producto_id UUID           NOT NULL REFERENCES public.productos(id),
    insumo_id   UUID           NOT NULL REFERENCES public.insumos(id),
    cantidad    NUMERIC(12, 3) NOT NULL CHECK (cantidad > 0),

    PRIMARY KEY (producto_id, insumo_id)
);

CREATE INDEX idx_producto_insumos_insumo ON public.producto_insumos (insumo_id);
