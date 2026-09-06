-- 038_combos_instancia.sql
-- Identificador de instancia de combo en detalles_comanda.
-- Agrupa los productos hijo que pertenecen a una misma unidad de combo pedida,
-- de modo que el visor de cocina pueda separar combos múltiples (2x, 3x, ...)
-- en unidades independientes en lugar de fusionarlos por nombre.
-- No lleva FK: referencia a una línea padre virtual que el POS no persiste.

ALTER TABLE public.detalles_comanda
    ADD COLUMN IF NOT EXISTS id_combo_padre UUID;