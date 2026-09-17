-- 048_movimiento_caja_metodo_opcional.sql
-- Ingresos de efectivo y cambio son movimientos físicos sin método de pago.
-- El backend los registra con metodo_pago_id = NULL.

ALTER TABLE public.movimientos_caja
    ALTER COLUMN metodo_pago_id DROP NOT NULL;
