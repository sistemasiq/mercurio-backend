-- 017_permisos_pulseras.sql
-- Permisos para administrar el catálogo de pulseras (alta/edición/baja).
-- La lectura de pulseras disponibles ya usaba estancias:checkin y se deja igual.
INSERT INTO public.permisos (codigo, nombre, modulo) VALUES
    ('pulseras:listar',   'Listar todas las pulseras de una sucursal', 'pulseras'),
    ('pulseras:crear',    'Registrar pulseras',                        'pulseras'),
    ('pulseras:editar',   'Editar pulseras',                           'pulseras'),
    ('pulseras:eliminar', 'Dar de baja pulseras',                      'pulseras')
ON CONFLICT (codigo) DO NOTHING;

-- AdministradorSistema (id=1): recibe todo lo nuevo que aún no tenga
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 1, p.id
FROM public.permisos p
WHERE NOT EXISTS (
    SELECT 1 FROM public.rol_permisos rp WHERE rp.rol_id = 1 AND rp.permiso_id = p.id
);

-- Administrador (id=2): gestión completa del catálogo de pulseras de su sucursal
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 2, id FROM public.permisos WHERE modulo = 'pulseras'
ON CONFLICT DO NOTHING;
