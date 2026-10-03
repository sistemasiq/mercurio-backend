-- =============================================================================
-- 073_administrador_permisos_turno.sql
-- Decisión del usuario (Ola C, C1): el Administrador debe poder abrir y cerrar
-- su propio turno de caja, igual que el Cajero. Tras la limpieza de 040, los
-- permisos reales del módulo son los de "turnos_caja" (no "pos"), así que se
-- toman los códigos vigentes de ese módulo para el rol Cajero (id=3):
-- turnos_caja:abrir, turnos_caja:conteo (contar) y turnos_caja:cancelar.
-- El Administrador (id=2) ya tenía turnos_caja:confirmar (cierre definitivo),
-- turnos_caja:ver_activo, turnos_caja:revision_admin e turnos_caja:historial
-- desde 021_permisos_corte_caja.sql.
-- No se otorgan permisos de venta POS (pos:acceder) porque el Administrador
-- no los tenía y la decisión del usuario pide no agregarlos.
-- =============================================================================

INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 2, p.id
FROM public.permisos p
WHERE p.codigo IN (
    'turnos_caja:abrir',
    'turnos_caja:conteo',
    'turnos_caja:cancelar'
)
AND NOT EXISTS (
    SELECT 1 FROM public.rol_permisos rp WHERE rp.rol_id = 2 AND rp.permiso_id = p.id
);
