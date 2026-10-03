-- 021_productos_combo.sql
-- FIX urgente: app/repositories/producto_repository.py y
-- app/repositories/combo_repository.py (mergeados en develop vía PR #3,
-- "feat: migrar almacenamiento de archivos a MinIO + productos combo")
-- ya leen/escriben productos.es_combo y la tabla producto_combo, pero
-- ninguna migración las había creado — cualquier alta/edición de producto
-- rompe con UndefinedColumnError desde ese merge. Esta migración cierra
-- el hueco de esquema.

ALTER TABLE public.productos
    ADD COLUMN IF NOT EXISTS es_combo BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS public.producto_combo (
    id              UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    combo_id        UUID           NOT NULL REFERENCES public.productos(id) ON DELETE CASCADE,
    producto_id     UUID           NOT NULL REFERENCES public.productos(id),
    cantidad        INTEGER        NOT NULL DEFAULT 1,

    activo          BOOLEAN     NOT NULL DEFAULT TRUE,
    creado          TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por      UUID        REFERENCES public.usuarios(id),
    modificado      TIMESTAMPTZ DEFAULT now(),
    modificado_por  UUID        REFERENCES public.usuarios(id),

    UNIQUE (combo_id, producto_id)
);

CREATE INDEX IF NOT EXISTS idx_producto_combo_combo ON public.producto_combo (combo_id);
