-- =============================================================================
-- 020_permisos_inventario_fase1.sql
-- Completa los permisos del módulo 'inventario' sembrado desde
-- 004_roles_permisos.sql (inventario:ver, gestionar_productos,
-- eliminar_producto, registrar_movimiento, gestionar_proveedores ya existían
-- pero solo protegían el CRUD de productos). Agrega los que faltan para
-- separar la gestión de insumos y el borrado de proveedores.
-- =============================================================================

INSERT INTO public.permisos (codigo, nombre, modulo) VALUES
    ('inventario:gestionar_insumos',  'Crear y editar insumos', 'inventario'),
    ('inventario:eliminar_insumo',    'Eliminar insumos',       'inventario'),
    ('inventario:eliminar_proveedor', 'Eliminar proveedores',   'inventario')
ON CONFLICT (codigo) DO NOTHING;

-- AdministradorSistema (id=1) y Administrador (id=2): gestión completa de inventario
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM public.roles r
CROSS JOIN public.permisos p
WHERE r.id IN (1, 2)
  AND p.codigo IN (
      'inventario:gestionar_insumos',
      'inventario:eliminar_insumo',
      'inventario:eliminar_proveedor'
  )
ON CONFLICT DO NOTHING;
