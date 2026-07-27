-- =============================================================================
-- 012_pulseras_inventario.sql
-- Permisos del módulo de inventario de pulseras RFID.
--
-- Las pulseras son de uso único (desechables): una vez asignada a un niño
-- (detalles_registro) o a un tutor (registros.pulseras_tutor_id) no vuelve a
-- aparecer como disponible. El estado se deriva en el cliente:
--   baja       = activo FALSE
--   en_uso     = activa pero ya asignada/consumida
--   disponible = activa y sin uso registrado
--
-- Aplicada manualmente en la BD dev el 2026-07-09.
-- =============================================================================

INSERT INTO public.permisos (codigo, nombre, modulo) VALUES
    ('pulseras:listar',   'Listar pulseras e inventario', 'pulseras'),
    ('pulseras:crear',    'Registrar pulseras nuevas',    'pulseras'),
    ('pulseras:editar',   'Editar pulseras',              'pulseras'),
    ('pulseras:eliminar', 'Eliminar pulseras',            'pulseras')
ON CONFLICT (codigo) DO NOTHING;

-- AdministradorSistema y Administrador (admin de sucursal): todos los permisos
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM public.roles r
CROSS JOIN public.permisos p
WHERE r.id IN (1, 2) AND p.modulo = 'pulseras'
ON CONFLICT DO NOTHING;
