-- 004_auth_tokens.sql
-- Refresh tokens (hash SHA-256, con rotación), revocación de access tokens (jti)
-- y sistema de permisos granular por rol. Refleja el esquema existente.

CREATE TABLE IF NOT EXISTS public.refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id  UUID NOT NULL REFERENCES public.usuarios(id),
    token_hash  TEXT NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    revocado    BOOLEAN NOT NULL DEFAULT FALSE,
    creado      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_usuario ON public.refresh_tokens (usuario_id);

-- Blacklist de access tokens por jti (verificada en cada request protegida).
CREATE TABLE IF NOT EXISTS public.tokens_revocados (
    jti         UUID PRIMARY KEY,
    expires_at  TIMESTAMPTZ NOT NULL,
    revocado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Permisos granulares y su asignación por rol.
CREATE TABLE IF NOT EXISTS public.permisos (
    id          INTEGER PRIMARY KEY,
    codigo      VARCHAR(100) NOT NULL UNIQUE,
    nombre      VARCHAR(150) NOT NULL,
    modulo      VARCHAR(100),
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS public.rol_permisos (
    rol_id     SMALLINT NOT NULL REFERENCES public.roles(id),
    permiso_id INTEGER NOT NULL REFERENCES public.permisos(id),
    PRIMARY KEY (rol_id, permiso_id)
);
