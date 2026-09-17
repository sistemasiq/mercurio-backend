-- =============================================================================
-- 046_retiro_parcial_devolucion.sql
-- Agrega 'Devolución' a conceptos_retiro y 'Cliente' a tipos_destinatario.
-- Solo cambio de esquema; la capa de aplicación se actualiza aparte.
-- =============================================================================

ALTER TYPE public.conceptos_retiro ADD VALUE IF NOT EXISTS 'Devolución';
ALTER TYPE public.tipos_destinatario ADD VALUE IF NOT EXISTS 'Cliente';
