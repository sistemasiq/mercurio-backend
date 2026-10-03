-- =============================================================================
-- 022_movimientos_inventario.sql
-- Fase 3 de inventario: ledger append-only de movimientos de stock. Fuente
-- de verdad de por qué cambió insumos.stock_actual (venta, cancelación,
-- entrada manual, merma). Nunca se edita ni se borra, por eso no tiene
-- columnas de auditoría estándar (activo/modificado/modificado_por).
-- =============================================================================

CREATE TABLE public.movimientos_inventario (
    id               UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id      UUID           NOT NULL REFERENCES public.sucursales(id),
    insumo_id        UUID           NOT NULL REFERENCES public.insumos(id),
    tipo             VARCHAR(1)     NOT NULL,  -- 'E'ntrada | 'S'alida | 'A'juste | 'M'erma
    cantidad         NUMERIC(12, 3) NOT NULL CHECK (cantidad > 0),
    stock_resultante NUMERIC(12, 3) NOT NULL,
    motivo           VARCHAR(30)    NOT NULL,  -- venta_comanda | cancelacion_comanda | entrada_manual | merma
    referencia_id    UUID,                     -- comanda_id cuando motivo es de venta/cancelación
    notas            TEXT,

    creado           TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por       UUID        REFERENCES public.usuarios(id)
);

CREATE INDEX idx_movimientos_inventario_insumo ON public.movimientos_inventario (insumo_id, creado DESC);
