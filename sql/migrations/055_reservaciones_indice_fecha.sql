-- =============================================================================
-- 055_reservaciones_indice_fecha.sql
-- Índice de apoyo para las consultas nuevas por sucursal + fecha: la
-- disponibilidad por bloque de horario (GET /reservaciones/disponibilidad)
-- y el calendario por rango (GET /reservaciones?desde&hasta), ambas filtran
-- por estas dos columnas.
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_reservaciones_sucursal_fecha
    ON public.reservaciones (sucursal_id, fecha_evento)
    WHERE activo = TRUE;
