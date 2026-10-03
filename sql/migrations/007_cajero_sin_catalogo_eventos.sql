-- =============================================================================
-- 007_cajero_sin_catalogo_eventos.sql
-- Ajuste de negocio: Cajero no necesita ver el catálogo de eventos
-- (extras, paquetes, tipos_evento, metodos_pago) — solo opera reservaciones,
-- caja y estancias. La 006 le había dado listar/ver de esos catálogos por
-- si acaso; se revoca.
-- =============================================================================

DELETE FROM public.rol_permisos
WHERE rol_id = 3  -- Cajero
  AND permiso_id IN (
    SELECT id FROM public.permisos
    WHERE modulo IN ('extras', 'paquetes', 'tipos_evento', 'metodos_pago')
  );
