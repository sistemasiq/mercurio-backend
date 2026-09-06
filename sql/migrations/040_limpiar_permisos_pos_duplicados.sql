-- =============================================================================
-- 040_limpiar_permisos_pos_duplicados.sql
-- El módulo "Pos" (pos:abrir_turno, pos:cerrar_turno, pos:ver_turnos) quedó como
-- duplicado muerto del módulo real "turnos_caja" (turnos_caja:abrir, :cancelar,
-- :historial): ningún endpoint del backend ni ninguna vista del frontend los
-- verifica (solo pos:acceder, que sí controla el menú "Caja (POS)", se conserva).
-- Además su asignación por rol no coincidía con la real: Administrador tenía
-- marcado "Abrir turno de caja" en Pos aunque turnos_caja:abrir (el que sí se
-- aplica) correctamente se lo niega — de ahí la confusión reportada de que
-- "a todos les aparece poder abrir caja" en el panel de roles.
-- ON DELETE CASCADE en rol_permisos.permiso_id limpia las asignaciones solas.
-- =============================================================================

DELETE FROM public.permisos
WHERE codigo IN ('pos:abrir_turno', 'pos:cerrar_turno', 'pos:ver_turnos');
