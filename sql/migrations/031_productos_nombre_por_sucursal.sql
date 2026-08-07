-- =============================================================================
-- 031_productos_nombre_por_sucursal.sql
-- productos.nombre tenía un UNIQUE global (productos_nombre_key), a
-- diferencia de tipos_evento/metodos_pago que ya se corrigieron con este
-- mismo patrón en 029_tipos_evento_metodos_pago_sucursal.sql. Dos franquicias
-- distintas nunca podían tener un producto con el mismo nombre (ej. "Agua",
-- "Refresco"), reventando con un 500 al crear.
--
-- productos.sucursal_id ya es NOT NULL (no existe concepto de producto
-- "global"), así que a diferencia de tipos_evento/metodos_pago no hace falta
-- ningún índice parcial adicional para el caso NULL.
-- =============================================================================

ALTER TABLE public.productos DROP CONSTRAINT IF EXISTS productos_nombre_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_productos_nombre_sucursal
    ON public.productos (nombre, sucursal_id);
