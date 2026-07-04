-- =============================================================================
-- 011_administrador_listar_sucursales.sql
-- La 008 le quitó a Administrador sucursales:listar/ver asumiendo que
-- siempre operaba una sola sucursal (la de su sesión). Ahora que un
-- Administrador puede tener varias sucursales asignadas via
-- usuarios_sucursal, necesita poder listar/ver sus propias sucursales
-- desde el frontend. branch_service.list_branches/get_branch ya limitan
-- el resultado a current_user.branch_id para este rol, así que solo hace
-- falta restaurar el permiso de solo lectura (no crear/editar/eliminar).
-- =============================================================================

INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 2, id FROM public.permisos  -- Administrador
WHERE codigo IN ('sucursales:listar', 'sucursales:ver')
ON CONFLICT DO NOTHING;
