-- =============================================================================
-- 044_compras_recepcion_parcial.sql
-- Fase 12: recepción parcial de compras. Hasta ahora `recibir` era todo-o-nada.
--   detalle_compras.cantidad_recibida: cuánto de la línea ya llegó (acumulado).
--   compras.estado gana el valor 'PARCIAL' (columna ensanchada de VARCHAR(1)).
-- =============================================================================

ALTER TABLE public.detalle_compras
    ADD COLUMN IF NOT EXISTS cantidad_recibida NUMERIC(12, 3) NOT NULL DEFAULT 0;

ALTER TABLE public.compras
    ALTER COLUMN estado TYPE VARCHAR(10);
