-- =============================================================================
-- 003_refresh_tokens.sql
-- Tabla para refresh tokens opacos (no JWT).
-- El token crudo se entrega al cliente; aquí se guarda su hash SHA-256.
-- =============================================================================

CREATE TABLE public.refresh_tokens (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id  UUID        NOT NULL REFERENCES public.usuarios(id) ON DELETE CASCADE,
    token_hash  TEXT        NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    revocado    BOOLEAN     NOT NULL DEFAULT FALSE,
    creado      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_refresh_token_hash UNIQUE (token_hash)
);

CREATE INDEX idx_refresh_tokens_usuario  ON public.refresh_tokens (usuario_id);
CREATE INDEX idx_refresh_tokens_expires  ON public.refresh_tokens (expires_at);
