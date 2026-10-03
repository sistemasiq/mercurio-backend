-- =============================================================================
-- 028_fix_pulsera_rfid_length.sql
-- Reconcilia el drift de esquema en pulseras.pulsera_rfid: la columna real
-- en la BD compartida quedó como CHAR(10) (aplicado manualmente, nunca
-- versionado), mientras que la migración 016_registro_infantes.sql ya
-- declara VARCHAR(50). El relleno con espacios de CHAR rompía el match
-- exacto del check-in por RFID y cualquier código de más de 10 caracteres
-- (ej. tags EPC Gen2, típicamente 24 hex) fallaba.
--
-- Ampliar CHAR(10) a VARCHAR(50) es una conversión segura: Postgres quita el
-- padding de espacios en el cast implícito y no trunca ningún dato existente.
-- =============================================================================

ALTER TABLE public.pulseras ALTER COLUMN pulsera_rfid TYPE VARCHAR(50);
