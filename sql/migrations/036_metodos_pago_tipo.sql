-- =============================================================================
-- 036_metodos_pago_tipo.sql
-- HALLAZGO: el modal de pago (FrontEnd) matcheaba el metodo de pago real del
-- catalogo de la sucursal buscando por coincidencia EXACTA de `nombre` contra
-- una de 4 etiquetas fijas ("Efectivo", "Tarjeta", "Cupones", "Lealtad"). Si
-- una sucursal nombraba su metodo distinto (ej. "Efectivo Angelopolis"), el
-- cobro truena aunque el metodo si exista y este activo.
--
-- Se agrega una categoria real e independiente del nombre libre, siguiendo
-- el mismo patron ya usado en productos.tipo (015_comandas_productos.sql):
-- VARCHAR(1) con codigos cortos en vez de un ENUM de Postgres.
--   E = Efectivo | T = Tarjeta (credito/debito/wallets) | C = Cupon
--   L = Lealtad  | O = Otro (cualquier metodo que no encaje en los anteriores,
--       ej. transferencias bancarias -- no tiene boton dedicado hoy en el
--       modal, pero tampoco se pierde: el FrontEnd puede listarlo aparte)
--
-- El backfill de filas existentes usa la misma heuristica por substring que
-- ya vivia hardcodeada en PaymentModal.vue (esEfectivo/esTarjeta), para no
-- inventar clasificaciones nuevas. Todo lo que no matchea ninguna regla cae
-- en 'O' via el DEFAULT.
-- =============================================================================

ALTER TABLE public.metodos_pago
    ADD COLUMN IF NOT EXISTS tipo VARCHAR(1) NOT NULL DEFAULT 'O'
        CHECK (tipo IN ('E', 'T', 'C', 'L', 'O'));

UPDATE public.metodos_pago SET tipo = 'E' WHERE nombre ILIKE '%efectivo%';
UPDATE public.metodos_pago SET tipo = 'T'
    WHERE nombre ILIKE '%tarjeta%'
       OR nombre ILIKE '%cr_dito%'
       OR nombre ILIKE '%d_bito%'
       OR nombre ILIKE '%pay%';
UPDATE public.metodos_pago SET tipo = 'C' WHERE nombre ILIKE '%cup_n%';
UPDATE public.metodos_pago SET tipo = 'L' WHERE nombre ILIKE '%lealtad%' OR nombre ILIKE '%puntos%';
