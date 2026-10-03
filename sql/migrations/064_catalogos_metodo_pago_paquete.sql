-- =============================================================================
-- 064_catalogos_metodo_pago_paquete.sql
-- WP B6, pendientes 1 y 3: campos de catálogo para paquetes y métodos de pago.
-- =============================================================================

-- Método de pago: comisión (informativa, p. ej. para conciliar terminal
-- bancaria) y si requiere capturar folio/referencia al cobrar.
ALTER TABLE public.metodos_pago
    ADD COLUMN IF NOT EXISTS comision_porcentaje NUMERIC(5, 2) NULL
        CHECK (comision_porcentaje IS NULL OR comision_porcentaje >= 0),
    ADD COLUMN IF NOT EXISTS requiere_referencia BOOLEAN NOT NULL DEFAULT FALSE;

-- Paquete: duración estimada del evento, bandera de "destacado" para
-- resaltarlo en selección, y porcentaje de anticipo sugerido.
ALTER TABLE public.paquetes
    ADD COLUMN IF NOT EXISTS duracion_horas NUMERIC(5, 2) NULL
        CHECK (duracion_horas IS NULL OR duracion_horas > 0),
    ADD COLUMN IF NOT EXISTS destacado BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS anticipo_porcentaje NUMERIC(5, 2) NULL
        CHECK (anticipo_porcentaje IS NULL OR
               (anticipo_porcentaje > 0 AND anticipo_porcentaje <= 100));
