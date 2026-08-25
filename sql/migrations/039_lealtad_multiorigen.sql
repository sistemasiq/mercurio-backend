-- =============================================================================
-- 039_lealtad_multiorigen.sql
-- Hasta ahora toda venta con celular capturado otorgaba puntos por igual,
-- sin distinguir origen. Se agregan 3 interruptores por sucursal
-- (configuracion_lealtad) para activar/desactivar el otorgamiento de puntos
-- según el origen del pago: comandas de caja, anticipos de reservación, o
-- check-in de niños (este último es un origen nuevo, antes no otorgaba
-- puntos en absoluto pese a que el modal de pago ya mostraba el saldo).
--
-- lotes_puntos/movimientos_puntos ganan registro_id como tercera referencia
-- de origen, mismo patrón ya usado para reservacion_id en la migración 035.
-- =============================================================================

ALTER TABLE public.configuracion_lealtad
    ADD COLUMN otorga_puntos_comandas      BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN otorga_puntos_reservaciones BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN otorga_puntos_checkin       BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE public.lotes_puntos
    ADD COLUMN registro_id UUID REFERENCES public.registros(id);

ALTER TABLE public.lotes_puntos
    DROP CONSTRAINT chk_lotes_puntos_una_referencia;

ALTER TABLE public.lotes_puntos
    ADD CONSTRAINT chk_lotes_puntos_una_referencia
    CHECK (num_nonnulls(comanda_id, reservacion_id, registro_id) = 1);

ALTER TABLE public.movimientos_puntos
    ADD COLUMN registro_id UUID REFERENCES public.registros(id);
