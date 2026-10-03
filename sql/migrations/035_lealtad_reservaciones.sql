-- =============================================================================
-- 035_lealtad_reservaciones.sql
-- lotes_puntos.comanda_id era NOT NULL, así que era imposible otorgar
-- puntos de lealtad por el anticipo de una reservación (no existe una
-- comanda asociada a ese pago) -- pese a que el modal de pago de
-- reservaciones ya captura el celular "para acumular puntos de lealtad".
--
-- Se permite comanda_id NULL y se agrega reservacion_id como referencia
-- alternativa; un CHECK exige que cada lote tenga exactamente una de las
-- dos. movimientos_puntos.comanda_id ya era nullable, solo se le agrega la
-- columna reservacion_id (sin CHECK: un movimiento de ajuste/cancelación
-- ya podía no tener referencia clara, no conviene sobre-restringir).
-- =============================================================================

ALTER TABLE public.lotes_puntos ALTER COLUMN comanda_id DROP NOT NULL;
ALTER TABLE public.lotes_puntos ADD COLUMN reservacion_id UUID REFERENCES public.reservaciones(id);
ALTER TABLE public.lotes_puntos ADD CONSTRAINT chk_lotes_puntos_una_referencia
    CHECK (num_nonnulls(comanda_id, reservacion_id) = 1);

ALTER TABLE public.movimientos_puntos ADD COLUMN reservacion_id UUID REFERENCES public.reservaciones(id);
