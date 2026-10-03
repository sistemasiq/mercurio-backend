-- 062_cajas_impresora.sql
-- Impresora de tickets asignada a la caja física.

ALTER TABLE public.cajas
    ADD COLUMN IF NOT EXISTS impresora VARCHAR(100) NULL;
