-- =============================================================================
-- 026_permisos_compras.sql
-- Completa el permiso de inventario que faltaba desde fase 1 (§3.3 de
-- INVENTARIO_DISENO.md): gestionar órdenes de compra a proveedor.
-- =============================================================================

INSERT INTO public.permisos (codigo, nombre, modulo) VALUES
    ('inventario:gestionar_compras', 'Crear y recibir órdenes de compra', 'inventario')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM public.roles r
CROSS JOIN public.permisos p
WHERE r.id IN (1, 2) AND p.codigo = 'inventario:gestionar_compras'
ON CONFLICT DO NOTHING;
