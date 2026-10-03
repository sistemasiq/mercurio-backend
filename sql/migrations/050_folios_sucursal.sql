-- 050_folios_sucursal.sql
-- Folio de ticket secuencial por sucursal (QA #21). El backend asigna
-- ticket_numero con un UPDATE ... RETURNING atómico dentro de la transacción
-- del cobro; el valor que mande el front en PagoCompletoRequest.ticket_numero
-- queda solo como fallback si por algún motivo no hay fila de folio.

CREATE TABLE IF NOT EXISTS public.folios_sucursal (
    sucursal_id UUID PRIMARY KEY REFERENCES public.sucursales(id),
    serie       TEXT NOT NULL DEFAULT 'A',
    ultimo      INTEGER NOT NULL DEFAULT 0
);
