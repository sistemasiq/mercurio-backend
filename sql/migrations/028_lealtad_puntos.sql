-- =============================================================================
-- 028_lealtad_puntos.sql
-- Módulo de puntos de lealtad: cashback en puntos por celular, scopeado por
-- sucursal (sin migración de puntos entre sucursales). Ver
-- PUNTOS_LEALTAD_DISENO.md y el plan de implementación en
-- /home/oscarmajai/.claude/plans/warm-jumping-hippo.md.
--
-- configuracion_lealtad es un "singleton" por sucursal (PK = sucursal_id,
-- se maneja con upsert). lotes_puntos es un lote por venta que otorga
-- puntos, con caducidad congelada al crearse (fecha_otorgado +
-- dias_caducidad de la config vigente en ese instante) y sin columna de
-- saldo cacheado: a diferencia de insumos.stock_actual, el saldo decae con
-- el tiempo sin ningún evento escrito, así que siempre se calcula al vuelo.
-- movimientos_puntos es el ledger de auditoría (otorgado/redimido/
-- cancelación/ajuste).
-- =============================================================================

CREATE TABLE public.configuracion_lealtad (
    sucursal_id        UUID           PRIMARY KEY REFERENCES public.sucursales(id) ON DELETE CASCADE,
    porcentaje_retorno NUMERIC(5, 2)  NOT NULL DEFAULT 0 CHECK (porcentaje_retorno BETWEEN 0 AND 100),
    dias_caducidad     INT            NOT NULL CHECK (dias_caducidad > 0),
    valor_punto        NUMERIC(10, 4) NOT NULL DEFAULT 1.00 CHECK (valor_punto > 0),
    activo             BOOLEAN        NOT NULL DEFAULT TRUE,

    creado             TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por         UUID        REFERENCES public.usuarios(id) ON DELETE SET NULL,
    modificado         TIMESTAMPTZ DEFAULT now(),
    modificado_por     UUID        REFERENCES public.usuarios(id) ON DELETE SET NULL
);

CREATE TABLE public.lotes_puntos (
    id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id        UUID        NOT NULL REFERENCES public.sucursales(id),
    celular            VARCHAR(10) NOT NULL,
    comanda_id         UUID        NOT NULL REFERENCES public.comandas(id),
    puntos_otorgados   INT         NOT NULL CHECK (puntos_otorgados > 0),
    puntos_disponibles INT         NOT NULL CHECK (puntos_disponibles >= 0),
    fecha_otorgado     TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_caducidad    TIMESTAMPTZ NOT NULL,
    creado_por         UUID        REFERENCES public.usuarios(id) ON DELETE SET NULL
);

CREATE INDEX idx_lotes_puntos_celular_sucursal ON public.lotes_puntos (celular, sucursal_id);
CREATE INDEX idx_lotes_puntos_vigencia ON public.lotes_puntos (sucursal_id, celular, fecha_caducidad)
    WHERE puntos_disponibles > 0;

CREATE TABLE public.movimientos_puntos (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id      UUID        NOT NULL REFERENCES public.sucursales(id),
    celular          VARCHAR(10) NOT NULL,
    lote_id          UUID        REFERENCES public.lotes_puntos(id),
    comanda_id       UUID        REFERENCES public.comandas(id),
    tipo             VARCHAR(1)  NOT NULL CHECK (tipo IN ('O', 'R', 'C', 'A')), -- Otorgado / Redimido / Cancelación / Ajuste
    puntos           INT         NOT NULL,
    saldo_resultante INT         NOT NULL,
    notas            TEXT,
    creado           TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por       UUID        REFERENCES public.usuarios(id) ON DELETE SET NULL
);

CREATE INDEX idx_movimientos_puntos_celular_sucursal ON public.movimientos_puntos (celular, sucursal_id, creado);
