-- =============================================================================
-- 058_lealtad_ajuste_manual.sql
-- Ajuste manual de puntos de lealtad (WP B4, pendiente 1): un administrador
-- puede otorgar o descontar puntos a mano (ej. compensación, corrección de un
-- error de captura), con motivo obligatorio para auditoría.
--
-- Permiso nuevo lealtad:ajustar, asignado a Administrador y
-- AdministradorSistema (sigue el patrón de 029_permisos_lealtad.sql / rol_id
-- 1=AdministradorSistema, 2=Administrador). No se asigna a Cajero: el canje
-- en caja ya usa lealtad:redimir, el ajuste manual es una corrección
-- administrativa, no una operación de venta.
--
-- Un ajuste positivo necesita un lote_puntos propio (igual que un
-- otorgamiento normal) para que ese saldo también caduque y participe en el
-- cálculo de "por_vencer" -- pero no tiene un origen de venta (no hay
-- comanda/reservación/registro detrás). El CHECK de lotes_puntos exigía
-- exactamente una referencia de origen (039_lealtad_multiorigen.sql); se
-- relaja a "cero o una" para permitir lotes de ajuste sin origen, sin
-- afectar la garantía de "a lo más una" para el resto de los casos.
-- =============================================================================

INSERT INTO public.permisos (codigo, nombre, modulo) VALUES
    ('lealtad:ajustar', 'Ajustar manualmente el saldo de puntos de un cliente', 'lealtad')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM public.roles r
CROSS JOIN public.permisos p
WHERE r.id IN (1, 2) AND p.codigo = 'lealtad:ajustar'
ON CONFLICT DO NOTHING;

ALTER TABLE public.lotes_puntos
    DROP CONSTRAINT chk_lotes_puntos_una_referencia;

ALTER TABLE public.lotes_puntos
    ADD CONSTRAINT chk_lotes_puntos_una_referencia
    CHECK (num_nonnulls(comanda_id, reservacion_id, registro_id) <= 1);
