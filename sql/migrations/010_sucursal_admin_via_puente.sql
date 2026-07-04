-- =============================================================================
-- 010_sucursal_admin_via_puente.sql
-- La asignación de administrador a una sucursal pasaba por dos columnas
-- planas en sucursales (administrador_id, administrador_name) que se
-- agregaron directo en código (commits e6a6323, 4779870, 640fab9, f756c7a)
-- sin migración versionada, y que además eran puramente decorativas: no
-- otorgaban acceso real, vivían desconectadas de usuarios_sucursal (la
-- tabla puente M:N que sí controla el acceso real, ver diseño original en
-- 001_initial_schema.sql).
--
-- Ahora que un Administrador puede tener varias sucursales, esa relación
-- pasa a vivir exclusivamente en usuarios_sucursal. Este script:
--   1. Hace backfill defensivo: si la columna administrador_id existe
--      (drift de un entorno donde se llegó a usar), migra cada asignación
--      a una fila real en usuarios_sucursal antes de perderla.
--   2. Elimina las columnas cosméticas de sucursales (DROP IF EXISTS,
--      porque en una base creada solo con las migraciones versionadas
--      esas columnas nunca existieron).
--   3. Agrega sucursal_id a refresh_tokens: al elegir sucursal activa en
--      login, esa elección debe sobrevivir la rotación de refresh token
--      sin tener que volver a derivarla desde usuarios_sucursal (que ya
--      no es 1:1 para Administrador).
-- =============================================================================

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'sucursales'
          AND column_name = 'administrador_id'
    ) THEN
        EXECUTE '
            INSERT INTO public.usuarios_sucursal (usuario_id, sucursal_id, creado_por)
            SELECT s.administrador_id, s.id, s.creado_por
            FROM public.sucursales s
            WHERE s.administrador_id IS NOT NULL
            ON CONFLICT (usuario_id, sucursal_id) DO NOTHING
        ';
    END IF;
END $$;

ALTER TABLE public.sucursales
    DROP COLUMN IF EXISTS administrador_id,
    DROP COLUMN IF EXISTS administrador_name;

ALTER TABLE public.refresh_tokens
    ADD COLUMN IF NOT EXISTS sucursal_id UUID REFERENCES public.sucursales(id) ON DELETE SET NULL;
