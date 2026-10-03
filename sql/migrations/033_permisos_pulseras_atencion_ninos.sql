-- =============================================================================
-- 033_permisos_pulseras_atencion_ninos.sql
-- El rol "Personal de atención de niños" debía tener los 4 permisos de
-- categoría estancias según 024_rol_personal_atencion_ninos.sql
-- (ver_activos, checkin, checkout, gestionar_pagos), pero la BD real
-- compartida solo tenía "estancias:ver_activos" -- drift entre la migración
-- versionada y lo aplicado realmente (mismo patrón ya documentado en el
-- proyecto para otras columnas/constraints). Además, nunca tuvo ningún
-- permiso de categoría pulseras salvo "pulseras:listar" -- pero el router de
-- pulseras exige también pulseras:crear/editar para las acciones que este
-- rol necesita en la práctica durante el check-in (vincular una pulsera
-- nueva al niño). Con esto, el rol queda con el set completo que su propia
-- descripción promete: "Registra entradas/salidas de niños y cobra
-- estancias en el módulo de Estancias."
--
-- No se incluye pulseras:eliminar: esa acción queda reservada a
-- Administrador.
-- =============================================================================

INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT (SELECT id FROM public.roles WHERE nombre = 'Personal de atención de niños'), id
FROM public.permisos
WHERE codigo IN (
    'estancias:checkin',
    'estancias:checkout',
    'estancias:gestionar_pagos',
    'pulseras:listar',
    'pulseras:crear',
    'pulseras:editar'
)
ON CONFLICT DO NOTHING;
