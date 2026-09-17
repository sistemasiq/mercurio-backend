-- =============================================================================
-- 043_movimiento_caja_tipo_ingreso.sql
-- Agrega el tipo de movimiento 'I' (Ingreso de efectivo) al enum
-- tipo_movimiento_caja.
--
-- Representa una entrada de efectivo físico durante un turno que no
-- corresponde a una venta (reposición de cambio, fondo adicional, etc.).
-- Mismo tratamiento que 'C' (Cambio, migración 042): se registra como
-- cualquier otro movimiento en movimientos_caja, sin tabla propia, con
-- metodo_pago_id=NULL (siempre es efectivo físico). A diferencia de 'RP' y
-- 'C', que se restan del efectivo esperado, 'I' se suma.
-- =============================================================================

ALTER TYPE public.tipo_movimiento_caja ADD VALUE 'I';

-- ── Permiso: registrar ingreso de efectivo ────────────────────────────────────
-- Bajo el módulo turnos_caja (como abrir/conteo/cancelar), no retiros_parciales:
-- el ingreso no tiene tabla propia, es una operación directa sobre el turno.
INSERT INTO public.permisos (codigo, nombre, modulo) VALUES
    ('turnos_caja:ingreso_efectivo', 'Registrar ingreso de efectivo en el turno', 'turnos_caja');

-- AdministradorSistema (id=1): todo lo nuevo
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 1, p.id
FROM public.permisos p
WHERE p.codigo = 'turnos_caja:ingreso_efectivo'
  AND NOT EXISTS (
    SELECT 1 FROM public.rol_permisos rp WHERE rp.rol_id = 1 AND rp.permiso_id = p.id
  );

-- Cajero (id=3): igual que retiros_parciales:crear
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 3, p.id
FROM public.permisos p
WHERE p.codigo = 'turnos_caja:ingreso_efectivo'
  AND NOT EXISTS (
    SELECT 1 FROM public.rol_permisos rp WHERE rp.rol_id = 3 AND rp.permiso_id = p.id
  );
