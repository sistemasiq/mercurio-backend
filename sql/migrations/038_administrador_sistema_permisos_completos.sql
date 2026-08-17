-- =============================================================================
-- 038_administrador_sistema_permisos_completos.sql
-- AdministradorSistema es el rol de "acceso total al sistema sin
-- restricción de sucursal" (004_roles_permisos.sql) y debería tener
-- siempre todos los permisos existentes. La 006 ya sembró ese backfill,
-- pero varias migraciones posteriores que agregaron permisos nuevos
-- (020, 023, 026, etc.) solo se los asignaron a roles inferiores y nunca
-- repitieron el backfill de rol_id=1, dejando a AdministradorSistema sin
-- permisos que sí tienen Administrador/Cajero/Cocina (pos:*, parte de
-- inventario:*, restaurante:*, reportes:*).
-- Idempotente: solo agrega lo que le falte, sin duplicar nada.
-- =============================================================================

INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 1, p.id
FROM public.permisos p
WHERE NOT EXISTS (
    SELECT 1 FROM public.rol_permisos rp WHERE rp.rol_id = 1 AND rp.permiso_id = p.id
);
