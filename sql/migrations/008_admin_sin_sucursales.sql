-- =============================================================================
-- 008_admin_sin_sucursales.sql
-- Administrador gestiona una sola sucursal (la suya) — no debe ver el
-- módulo de gestión de sucursales de la franquicia, eso es exclusivo de
-- AdministradorSistema. Se revoca sucursales:listar/ver.
-- =============================================================================

DELETE FROM public.rol_permisos
WHERE rol_id = 2  -- Administrador
  AND permiso_id IN (
    SELECT id FROM public.permisos
    WHERE codigo IN ('sucursales:listar', 'sucursales:ver')
  );
