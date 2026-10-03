-- 049_pagos_idempotencia.sql
-- Soporta el header Idempotency-Key de POST /pagos/completar (QA #20).
-- Si la clave ya existe con el mismo hash de payload, el backend devuelve la
-- comanda original sin volver a cobrar; si existe con otro hash, 409.

CREATE TABLE IF NOT EXISTS public.pagos_idempotencia (
    clave        TEXT PRIMARY KEY,
    sucursal_id  UUID NOT NULL REFERENCES public.sucursales(id),
    usuario_id   UUID NOT NULL REFERENCES public.usuarios(id),
    hash_payload TEXT NOT NULL,
    comanda_id   UUID NOT NULL REFERENCES public.comandas(id),
    creado       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pagos_idempotencia_comanda
    ON public.pagos_idempotencia (comanda_id);
