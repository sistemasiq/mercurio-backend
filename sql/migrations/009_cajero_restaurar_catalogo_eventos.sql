-- =============================================================================
-- 009_cajero_restaurar_catalogo_eventos.sql
-- La 007 le quito a Cajero listar/ver de extras/paquetes/tipos_evento/
-- metodos_pago asumiendo que no los necesitaba. Pero Cajero conserva
-- reservaciones:crear y el stepper de "Nueva Reservacion" requiere esos
-- 4 catalogos (tipo de evento, paquetes y extras, metodo de pago) para
-- completarse. Sin ellos, Cajero puede entrar al formulario pero los
-- catalogos se muestran vacios. Se restaura solo listar/ver (lectura),
-- no crear/editar/eliminar.
-- =============================================================================

INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 3, id FROM public.permisos
WHERE modulo IN ('extras', 'paquetes', 'tipos_evento', 'metodos_pago')
  AND (codigo LIKE '%:listar' OR codigo LIKE '%:ver')
ON CONFLICT DO NOTHING;
