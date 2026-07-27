-- 022_comandas_auditoria_combos.sql
-- Columnas que requiere el PR "feat: pagos multimodales, auditoria y
-- expansion de combos en backend" (feature/complementos-comandas):
-- auditoría de creado_por/modificado_por y cancelación con motivo en
-- comandas, y desglose de combos (nombre_combo_padre/es_hijo_de/
-- es_hijo_combo) + soft-delete (activo) en detalles_comanda. El PR asume
-- estas columnas en app/repositories/comanda_repository.py pero no traía
-- migración — se agregan aquí antes de mergearlo.

ALTER TABLE public.comandas
    ADD COLUMN IF NOT EXISTS activo          BOOLEAN     NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS motivo_cancelacion TEXT,
    ADD COLUMN IF NOT EXISTS creado_por      UUID        REFERENCES public.usuarios(id),
    ADD COLUMN IF NOT EXISTS modificado      TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS modificado_por  UUID        REFERENCES public.usuarios(id);

ALTER TABLE public.detalles_comanda
    ADD COLUMN IF NOT EXISTS activo             BOOLEAN     NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS nombre_combo_padre VARCHAR(150),
    ADD COLUMN IF NOT EXISTS es_hijo_de         UUID        REFERENCES public.productos(id),
    ADD COLUMN IF NOT EXISTS es_hijo_combo      BOOLEAN     NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS creado_por         UUID        REFERENCES public.usuarios(id),
    ADD COLUMN IF NOT EXISTS modificado         TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS modificado_por     UUID        REFERENCES public.usuarios(id);
