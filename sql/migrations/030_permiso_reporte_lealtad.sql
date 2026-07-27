-- =============================================================================
-- 030_permiso_reporte_lealtad.sql
-- Permiso para el reporte agregado de puntos de lealtad por sucursal
-- (fase 5, agregada tras validar con el usuario que no era viable sin
-- backend nuevo — los puntos se indexan por celular, no hay lista de
-- "todos los celulares" que agregar solo en el cliente).
-- =============================================================================

INSERT INTO public.permisos (codigo, nombre, modulo) VALUES
    ('lealtad:ver_reporte', 'Ver reporte agregado de puntos de lealtad', 'lealtad')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM public.roles r
CROSS JOIN public.permisos p
WHERE r.id IN (1, 2) AND p.codigo = 'lealtad:ver_reporte'
ON CONFLICT DO NOTHING;
