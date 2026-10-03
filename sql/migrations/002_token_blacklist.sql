-- =============================================================================
-- 002_token_blacklist.sql
-- Tabla para revocar access tokens por jti antes de su expiración natural.
-- =============================================================================

CREATE TABLE public.tokens_revocados (
    jti         UUID        PRIMARY KEY,
    expires_at  TIMESTAMPTZ NOT NULL,
    revocado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Permite limpiar tokens ya expirados eficientemente
CREATE INDEX idx_tokens_revocados_expires ON public.tokens_revocados (expires_at);
