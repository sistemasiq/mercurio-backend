-- =============================================================================
-- 054_pagos_reservacion_tipo.sql
-- Distingue anticipo / pago / liquidación en cada pago de reservación.
-- Backfill: los pagos cuyas notas empiezan con "Anticipo" pasan a 'anticipo'
-- (ver el texto que ya graba NuevaReservacionPage.vue al cobrar el anticipo).
-- =============================================================================

ALTER TABLE public.pagos_reservacion
    ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'pago';

ALTER TABLE public.pagos_reservacion
    ADD CONSTRAINT pagos_reservacion_tipo_check
    CHECK (tipo IN ('anticipo', 'pago', 'liquidacion'));

UPDATE public.pagos_reservacion
SET tipo = 'anticipo'
WHERE notas ILIKE 'Anticipo%'
  AND tipo = 'pago';
