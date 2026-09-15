-- =============================================================================
-- 046_config_impresora.sql
-- Configuración de impresoras por sucursal (filosofía 1 botón = imprimir).
--
-- Guarda la impresora por defecto para tickets y otra para etiquetas por
-- sucursal. El frontend solo hace api.imprimirTicketDirecto(data) y el
-- backend resuelve el nombre_impresora exacto como aparece en Windows
-- (ej: "IMPRESORA-OFICHIDO") sin VID/PID ni SDK de marca.
--
-- Soporta dos tipos por sucursal: 'ticket' (58mm/80mm parametrizado) y
-- 'etiqueta' (60x40mm). La detección heurística (DriverName + PaperNames)
-- se guarda en tipo_detectado/driver_detectado pero el usuario puede hacer
-- override manual (override_manual).
-- =============================================================================

DO $$ BEGIN
    CREATE TYPE tipo_impresora_tipo AS ENUM ('ticket', 'etiqueta');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE tipo_impresora_detectado AS ENUM ('ticket_58', 'ticket_80', 'etiqueta_60x40', 'a4', 'desconocida');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS public.config_impresora (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id         UUID            NOT NULL REFERENCES public.sucursales(id) ON DELETE CASCADE,
    tipo                tipo_impresora_tipo NOT NULL, -- 'ticket' | 'etiqueta'
    nombre_impresora    TEXT            NOT NULL,
    ancho_mm            INT             NOT NULL DEFAULT 58, -- 58 | 80 | 60
    alto_mm             INT,                               -- 40 para etiqueta
    driver_detectado    TEXT,
    tipo_detectado      tipo_impresora_detectado NOT NULL DEFAULT 'desconocida',
    paper_names         TEXT[]          DEFAULT '{}',
    override_manual     BOOLEAN         NOT NULL DEFAULT FALSE,
    creado_por          UUID            REFERENCES public.usuarios(id),
    creado              TIMESTAMPTZ     NOT NULL DEFAULT now(),
    modificado          TIMESTAMPTZ,
    modificado_por      UUID            REFERENCES public.usuarios(id),
    CONSTRAINT uq_config_impresora_sucursal_tipo UNIQUE (sucursal_id, tipo)
);

