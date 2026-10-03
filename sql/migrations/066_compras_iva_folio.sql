-- =============================================================================
-- 066_compras_iva_folio.sql
-- WP B6, pendiente 6: IVA de la compra y folio de orden de compra. El folio
-- sigue el mismo mecanismo de secuencia por sucursal que folios_sucursal
-- (migración 050 / app/repositories/folio_repository.py), pero en una tabla
-- propia porque esa es específica del folio de ticket de comanda (serie 'A',
-- truncado a 10 chars). Si la app no puede generarlo (p. ej. backfill o
-- captura manual), folio queda NULL o con el valor capturado por el usuario.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.folios_compra_sucursal (
    sucursal_id UUID PRIMARY KEY REFERENCES public.sucursales(id),
    serie       TEXT NOT NULL DEFAULT 'OC',
    ultimo      INTEGER NOT NULL DEFAULT 0
);

ALTER TABLE public.compras
    ADD COLUMN IF NOT EXISTS iva NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (iva >= 0),
    ADD COLUMN IF NOT EXISTS folio VARCHAR(20) NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_compras_sucursal_folio
    ON public.compras (sucursal_id, folio)
    WHERE folio IS NOT NULL;
