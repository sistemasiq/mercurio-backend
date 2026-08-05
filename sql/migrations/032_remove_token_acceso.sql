-- 032_remove_token_acceso.sql
-- Elimina la columna token_acceso de la tabla tutores.
-- Ahora se usa directamente el campo id (UUID) del tutor como token
-- para el "Visor de Padres".
ALTER TABLE public.tutores
    DROP COLUMN IF EXISTS token_acceso;
