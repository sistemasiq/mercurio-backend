-- 047_registros_datos_adicionales.sql
-- Campos usados por el flujo actual de registro de estancias.
-- IF NOT EXISTS permite actualizar instalaciones locales que ya tienen datos.

ALTER TABLE public.registros
    ADD COLUMN IF NOT EXISTS nombre_segundo_tutor VARCHAR(200),
    ADD COLUMN IF NOT EXISTS reservacion_id UUID REFERENCES public.reservaciones(id);

CREATE INDEX IF NOT EXISTS idx_registros_reservacion_id
    ON public.registros (reservacion_id);
