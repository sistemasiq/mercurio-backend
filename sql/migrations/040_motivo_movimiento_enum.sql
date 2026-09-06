-- =============================================================================
-- 040_motivo_movimiento_enum.sql
-- movimientos_inventario.motivo era VARCHAR(30) con el conjunto de valores solo
-- documentado en un comentario. Se convierte a ENUM para que la BD garantice el
-- dominio, igual que tipo_producto / metodo_pago_tipo en el resto del esquema.
-- Se incluyen desde ya los valores de fases siguientes (conteo_fisico, ajuste_fifo)
-- para no tener que hacer ALTER TYPE ADD VALUE después.
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'motivo_movimiento_inventario') THEN
        CREATE TYPE motivo_movimiento_inventario AS ENUM (
            'venta_comanda',
            'cancelacion_comanda',
            'entrada_manual',
            'merma',
            'compra',
            'conteo_fisico',
            'ajuste_fifo'
        );
    END IF;
END$$;

ALTER TABLE public.movimientos_inventario
    ALTER COLUMN motivo TYPE motivo_movimiento_inventario
    USING motivo::motivo_movimiento_inventario;
