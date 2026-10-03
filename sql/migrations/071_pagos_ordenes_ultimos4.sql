-- 071_pagos_ordenes_ultimos4.sql
-- Últimos 4 dígitos de la tarjeta, opcionales, para el pago de una comanda.
-- Pendiente B9 B.1 (dejado por B1).

ALTER TABLE public.pagos_ordenes
    ADD COLUMN IF NOT EXISTS ultimos4 VARCHAR(4) NULL;
