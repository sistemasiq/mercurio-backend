-- =============================================================================
-- 047_pulsera_rfid_formato_wk.sql
-- El formato oficial de número de pulsera es WK-0000000 (10 caracteres fijos).
-- Se ajusta la columna de VARCHAR(50) a VARCHAR(10) y se agrega un CHECK que
-- exige el patrón WK- seguido de 7 dígitos.
--
-- NOT VALID: el constraint aplica solo a inserts/updates futuros;
-- las filas de prueba existentes no se validan ni se borran.
-- =============================================================================

ALTER TABLE public.pulseras
    ALTER COLUMN pulsera_rfid TYPE VARCHAR(10),
    ADD CONSTRAINT chk_pulsera_rfid_formato
        CHECK (pulsera_rfid ~ '^WK-[0-9]{7}$') NOT VALID;
