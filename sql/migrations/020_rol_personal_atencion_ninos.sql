-- =============================================================================
-- 020_rol_personal_atencion_ninos.sql
-- Nuevo rol solicitado por el negocio: personal que atiende el módulo de
-- Estancias (check-in/check-out de niños y cobros de estancia), sin acceso
-- a caja, inventario ni reservaciones. Sigue el mismo patrón que 004/006/017
-- (rol nuevo + asignación de permisos existentes).
-- =============================================================================

INSERT INTO public.roles (nombre, descripcion) VALUES
    ('Personal de atención de niños',
     'Registra entradas/salidas de niños y cobra estancias en el módulo de Estancias.');

INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT (SELECT id FROM public.roles WHERE nombre = 'Personal de atención de niños'), id
FROM public.permisos
WHERE codigo IN (
    'estancias:ver_activos',
    'estancias:checkin',
    'estancias:checkout',
    'estancias:gestionar_pagos'
);
