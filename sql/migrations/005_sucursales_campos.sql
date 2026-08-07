ALTER TABLE public.sucursales
    DROP COLUMN IF EXISTS clave,
    DROP COLUMN IF EXISTS ciudad,
    DROP COLUMN IF EXISTS estado_geo,
    DROP COLUMN IF EXISTS gerente;