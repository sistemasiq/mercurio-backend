-- =============================================================================
-- 041_producto_insumos_auditoria.sql
-- La receta (producto_insumos) era una tabla puente pura, sin auditoría. Pero
-- cambiar la cantidad de un insumo en una receta desplaza el costo (COGS) de
-- todas las ventas futuras de ese producto — es un cambio con peso financiero
-- y hasta ahora no quedaba rastro de quién ni cuándo. Se agregan columnas de
-- auditoría (nullable / con default) sin romper el patrón de PK compuesta.
-- =============================================================================

ALTER TABLE public.producto_insumos
    ADD COLUMN IF NOT EXISTS creado         TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS creado_por     UUID REFERENCES public.usuarios(id),
    ADD COLUMN IF NOT EXISTS modificado     TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS modificado_por UUID REFERENCES public.usuarios(id);
