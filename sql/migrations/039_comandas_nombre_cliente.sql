-- 039_comandas_nombre_cliente.sql
-- Nombre del cliente para comandas de mostrador / para llevar.
-- Permite identificar a quién entregar el pedido en cocina y en historial.

ALTER TABLE public.comandas
    ADD COLUMN IF NOT EXISTS nombre_cliente VARCHAR(150);