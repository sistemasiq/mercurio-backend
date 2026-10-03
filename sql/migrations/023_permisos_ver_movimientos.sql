-- =============================================================================
-- 023_permisos_ver_movimientos.sql
-- Completa el permiso de inventario que faltaba desde fase 1: ver el
-- historial de movimientos de stock. Cajero lo necesita para consultar el
-- historial de un insumo antes de registrar un ajuste manual.
-- =============================================================================

INSERT INTO public.permisos (codigo, nombre, modulo) VALUES
    ('inventario:ver_movimientos', 'Ver historial de movimientos de inventario', 'inventario')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM public.roles r
CROSS JOIN public.permisos p
WHERE r.id IN (1, 2, 3) AND p.codigo = 'inventario:ver_movimientos'
ON CONFLICT DO NOTHING;
