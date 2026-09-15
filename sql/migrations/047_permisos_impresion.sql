-- 047_permisos_impresion.sql
-- Permiso para configurar impresoras por sucursal

INSERT INTO public.permisos (codigo, descripcion) VALUES
  ('impresion:configurar', 'Configurar impresoras por sucursal (tickets/etiquetas)')
ON CONFLICT (codigo) DO NOTHING;

-- Asignar a AdministradorSistema (1) y Administrador (2) si existen
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id FROM public.roles r, public.permisos p
WHERE r.nombre IN ('AdministradorSistema','Administrador') AND p.codigo='impresion:configurar'
ON CONFLICT DO NOTHING;
