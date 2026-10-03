-- =============================================================================
-- 067_ws_tickets.sql
-- Tickets efímeros de un solo uso para autenticar WebSockets (comandas,
-- estancias) sin exponer el JWT en la URL. Se guarda el hash SHA-256 del
-- ticket crudo (igual que refresh_tokens) y los claims mínimos necesarios
-- para reconstruir el TokenData sin volver a tocar la tabla de usuarios.
-- Vida útil corta (30 s); se usa tabla (no memoria) porque el despliegue
-- puede escalar a varios workers.
-- =============================================================================

CREATE TABLE public.ws_tickets (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_hash TEXT        NOT NULL,
    claims      JSONB       NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    usado       BOOLEAN     NOT NULL DEFAULT FALSE,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_ws_tickets_hash UNIQUE (ticket_hash)
);

CREATE INDEX idx_ws_tickets_expires ON public.ws_tickets (expires_at);
