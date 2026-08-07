-- =============================================================================
-- 032_paquetes_quitar_duracion.sql
-- Quita duracion_minutos de paquetes: era un campo puramente informativo
-- (nunca afectó el precio) que quedó redundante y confuso una vez que se
-- agregó precio_hora (031_paquetes_precio_hora.sql) — las horas que
-- realmente definen el cobro son las que el cliente elige libremente en
-- el paso 1 de la reservación (hora_inicio/hora_fin), no la duración
-- "sugerida" del paquete.
-- =============================================================================

ALTER TABLE public.paquetes
    DROP COLUMN IF EXISTS duracion_minutos;
