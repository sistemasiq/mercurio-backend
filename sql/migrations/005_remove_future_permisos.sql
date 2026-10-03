-- =============================================================================
-- 005_remove_future_permisos.sql
-- Elimina los permisos de módulos sin endpoints implementados:
-- pos, inventario, restaurante, reportes.
-- Solo quedan activos los permisos con endpoints reales:
-- usuarios (5), sucursales (5), permisos (2) = 12 permisos.
-- =============================================================================

DELETE FROM public.rol_permisos
WHERE permiso_id IN (
    SELECT id FROM public.permisos
    WHERE modulo IN ('pos', 'inventario', 'restaurante', 'reportes')
);

DELETE FROM public.permisos
WHERE modulo IN ('pos', 'inventario', 'restaurante', 'reportes');
