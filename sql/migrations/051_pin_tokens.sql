-- 051_pin_tokens.sql
-- Token de un solo uso emitido al validar el PIN del cajero/admin en el
-- cierre de caja (QA #14). POST /turnos-caja/confirmar exige los tokens de
-- ambos roles y los marca como usados.

CREATE TABLE IF NOT EXISTS public.pin_tokens (
    token      TEXT PRIMARY KEY,
    usuario_id UUID NOT NULL REFERENCES public.usuarios(id),
    turno_id   UUID NOT NULL REFERENCES public.apertura_caja(id),
    rol        VARCHAR(20) NOT NULL,
    creado     TIMESTAMPTZ NOT NULL DEFAULT now(),
    expira     TIMESTAMPTZ NOT NULL,
    usado      BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_pin_tokens_turno
    ON public.pin_tokens (turno_id);
