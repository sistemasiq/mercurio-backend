-- 018_registros_pulsera_tutor.sql
-- Agrega la columna que el commit de "pulseras disponibles" (feature
-- registro-infantes-integration) ya consulta (registros.pulseras_tutor_id)
-- pero que nunca se agregó a la BD ni se llena desde el flujo de check-in.
-- Nullable: ningún registro existente ni el flujo actual de creación la
-- asigna todavía; queda lista para cuando se implemente la pulsera del
-- tutor de punta a punta (endpoint de check-in + UI).
ALTER TABLE public.registros
    ADD COLUMN IF NOT EXISTS pulseras_tutor_id UUID REFERENCES public.pulseras(id);
