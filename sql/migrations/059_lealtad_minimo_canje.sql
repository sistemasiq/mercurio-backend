-- =============================================================================
-- 059_lealtad_minimo_canje.sql
-- Mínimo de puntos requerido para poder canjear (WP B4, pendiente 3). Antes
-- cualquier saldo > 0 permitía redimir; algunos programas de lealtad
-- requieren acumular un piso antes de poder usarlos. DEFAULT 0 mantiene el
-- comportamiento actual (sin mínimo) en toda sucursal existente.
-- =============================================================================

ALTER TABLE public.configuracion_lealtad
    ADD COLUMN minimo_canje INT NOT NULL DEFAULT 0 CHECK (minimo_canje >= 0);
