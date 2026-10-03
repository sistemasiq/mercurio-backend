-- 072_comandas_mesa.sql
-- Mesa del pedido, opcional, para la comanda de caja/cocina. Pendiente B9
-- B.2 (dejado por B1).

ALTER TABLE public.comandas
    ADD COLUMN IF NOT EXISTS mesa VARCHAR(20) NULL;
