-- 031_padres_visor_token.sql
-- Agrega columna token_acceso a la tabla tutores para el "Visor de Padres".
-- Cada tutor recibe un UUID único que se codifica en su código QR.
-- El QR se escanea y el token se envía al backend para obtener el dashboard.
ALTER TABLE public.tutores
    ADD COLUMN IF NOT EXISTS token_acceso UUID UNIQUE;
