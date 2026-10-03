-- =============================================================================
-- 065_catalogos_producto_proveedor.sql
-- WP B6, pendientes 4 y 5: código único de producto (por sucursal) y datos
-- fiscales/logísticos de proveedor.
-- =============================================================================

ALTER TABLE public.productos
    ADD COLUMN IF NOT EXISTS codigo VARCHAR(50) NULL;

-- Único por sucursal (un producto global sin sucursal no aplicaría aquí: la
-- tabla ya exige sucursal_id NOT NULL). Índice parcial para no chocar entre
-- filas con codigo NULL (varios productos sin código).
CREATE UNIQUE INDEX IF NOT EXISTS idx_productos_sucursal_codigo
    ON public.productos (sucursal_id, codigo)
    WHERE codigo IS NOT NULL;

ALTER TABLE public.proveedores
    ADD COLUMN IF NOT EXISTS rfc VARCHAR(13) NULL,
    ADD COLUMN IF NOT EXISTS dias_entrega INT NULL CHECK (dias_entrega IS NULL OR dias_entrega >= 0);
