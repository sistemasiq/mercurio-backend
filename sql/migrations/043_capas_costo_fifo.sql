-- =============================================================================
-- 043_capas_costo_fifo.sql
-- Fase 11: costeo PEPS/FIFO. Hasta ahora insumos.costo_unitario se sobrescribía
-- con el costo de la última compra y no había forma de valuar el consumo.
--
-- Cada entrada de stock (compra, entrada manual, devolución por cancelación,
-- conteo positivo) crea una CAPA con su costo. El consumo (venta, merma, conteo
-- negativo) agota las capas más viejas primero y registra su costo en
-- movimientos_inventario.costo_total. insumos.costo_unitario pasa a ser el
-- promedio ponderado de las capas con stock restante (valor de referencia para
-- la UI y el "valor de inventario").
--
-- Invariante: SUM(cantidad_restante) por insumo == insumos.stock_actual.
-- =============================================================================

CREATE TABLE public.capas_costo_insumo (
    id                UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    insumo_id         UUID           NOT NULL REFERENCES public.insumos(id),
    cantidad_inicial  NUMERIC(12, 3) NOT NULL CHECK (cantidad_inicial > 0),
    cantidad_restante NUMERIC(12, 3) NOT NULL CHECK (cantidad_restante >= 0),
    costo_unitario    NUMERIC(12, 4) NOT NULL,  -- por unidad base del insumo
    origen            VARCHAR(20)    NOT NULL,   -- compra | entrada_manual | devolucion | conteo | inicial
    referencia_id     UUID,                      -- compra_id / comanda_id según origen
    creado            TIMESTAMPTZ    NOT NULL DEFAULT now()
);

-- Orden FIFO: las capas más viejas con stock se consumen primero.
CREATE INDEX idx_capas_insumo_fifo
    ON public.capas_costo_insumo (insumo_id, creado, id)
    WHERE cantidad_restante > 0;

ALTER TABLE public.movimientos_inventario
    ADD COLUMN IF NOT EXISTS costo_total NUMERIC(14, 4);

-- Backfill: una capa "inicial" por cada insumo que ya tiene stock, al costo
-- unitario vigente (o 0 si no estaba definido).
INSERT INTO public.capas_costo_insumo
    (insumo_id, cantidad_inicial, cantidad_restante, costo_unitario, origen)
SELECT id, stock_actual, stock_actual, COALESCE(costo_unitario, 0), 'inicial'
FROM public.insumos
WHERE stock_actual > 0;
