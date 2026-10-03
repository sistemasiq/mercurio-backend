-- =============================================================================
-- 042_insumos_reorden.sql
-- Fase 9: el insumo solo tenía stock_minimo (umbral crítico). Se agregan:
--   punto_reorden: nivel al que conviene volver a pedir (antes de tocar el
--                  mínimo), para poder alertar con margen.
--   stock_maximo:  tope de referencia para sugerir cuánto comprar.
-- Ambos nullables: si no se define punto_reorden, la alerta de reorden usa
-- stock_minimo como fallback.
-- =============================================================================

ALTER TABLE public.insumos
    ADD COLUMN IF NOT EXISTS punto_reorden NUMERIC(12, 3),
    ADD COLUMN IF NOT EXISTS stock_maximo  NUMERIC(12, 3);
