-- =============================================================================
-- 032_fix_sucursales_telefono_length.sql
-- Reconcilia el drift de esquema en sucursales.telefono: la columna real en
-- la BD compartida quedó como VARCHAR(15), mientras que la migración
-- 001_initial_schema.sql ya declaraba VARCHAR(20). Un teléfono con el mismo
-- formato que sugiere el placeholder del formulario ("+52 000 000 0000",
-- 16 caracteres) reventaba con un StringDataRightTruncationError (500) sin
-- manejar.
--
-- Ampliar VARCHAR(15) a VARCHAR(20) es una conversión segura: no trunca
-- ningún dato existente (solo agranda el límite).
-- =============================================================================

ALTER TABLE public.sucursales ALTER COLUMN telefono TYPE VARCHAR(20);
