-- =============================================================================
-- 029_permisos_lealtad.sql
-- Permisos del módulo de puntos de lealtad. rol_id 1=AdministradorSistema,
-- 2=Administrador, 3=Cajero (el canje ocurre en caja, por eso Cajero
-- también necesita ver_saldo/redimir, no solo gestionar_configuracion).
-- =============================================================================

INSERT INTO public.permisos (codigo, nombre, modulo) VALUES
    ('lealtad:gestionar_configuracion', 'Configurar % de retorno, caducidad y valor del punto por sucursal', 'lealtad'),
    ('lealtad:ver_saldo', 'Consultar saldo y kardex de puntos de un cliente', 'lealtad'),
    ('lealtad:redimir', 'Canjear puntos como descuento al cobrar', 'lealtad')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM public.roles r
CROSS JOIN public.permisos p
WHERE r.id IN (1, 2) AND p.codigo = 'lealtad:gestionar_configuracion'
ON CONFLICT DO NOTHING;

INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM public.roles r
CROSS JOIN public.permisos p
WHERE r.id IN (1, 2, 3) AND p.codigo IN ('lealtad:ver_saldo', 'lealtad:redimir')
ON CONFLICT DO NOTHING;
