-- =============================================================================
-- 034_quitar_alcance_global.sql
-- Decisión de producto: ningún catálogo debe tener alcance "Global"
-- (compartido entre todas las sucursales/franquicias) -- cada sucursal
-- maneja sus propios extras/tipos_evento/metodos_pago de forma exclusiva.
--
-- Auditoría previa (2026-07-27): los 28 registros con sucursal_id IS NULL
-- (11 extras, 11 tipos_evento, 6 metodos_pago) tienen creado_por = NULL --
-- son datos de seed/demo sin ningún rastro de qué sucursal los originó. No
-- existe una "sucursal de origen" recuperable. Además, 11 reservaciones y
-- 20 pagos_reservacion reales de MÚLTIPLES sucursales ya referencian estos
-- tipos_evento/metodos_pago globales por FK -- no se pueden borrar sin
-- romper ese historial.
--
-- Decisión confirmada con el usuario: asignar los 28 registros legados a
-- una sola sucursal fija, la más antigua (Plaza Colibrí, SUC-02-CL,
-- id 1eb11d0c-8a9c-468d-bbc6-0e649e9bfcf2, creada 2026-06-12). Las demás
-- sucursales que ya usaban estos catálogos en su historial conservan sus
-- reservaciones/pagos intactos (el FK sigue apuntando al mismo id), pero
-- dejan de verlos en sus pantallas de administración de catálogo -- es la
-- consecuencia esperada y aceptada de esta decisión.
--
-- reset_db_local.sh (reconstrucción desde cero): en ese punto la tabla
-- sucursales todavía está vacía (el seed corre DESPUÉS de las migraciones),
-- así que el id fijo de Plaza Colibrí no existe y el UPDATE reventaba con
-- FK violation. El bloque de abajo cae a: Plaza Colibrí si existe (BD
-- compartida), si no la sucursal más antigua que haya, y si no hay ninguna
-- (rebuild puro) elimina las filas globales -- que ahí son solo datos demo
-- sembrados por migraciones previas, sin ningún pago/reservación real que
-- las referencie todavía.
-- =============================================================================

DO $$
DECLARE
    destino UUID;
BEGIN
    SELECT COALESCE(
        (SELECT id FROM public.sucursales WHERE id = '1eb11d0c-8a9c-468d-bbc6-0e649e9bfcf2'),
        (SELECT id FROM public.sucursales ORDER BY creado NULLS FIRST, id LIMIT 1)
    ) INTO destino;

    IF destino IS NOT NULL THEN
        UPDATE public.extras       SET sucursal_id = destino WHERE sucursal_id IS NULL;
        UPDATE public.tipos_evento SET sucursal_id = destino WHERE sucursal_id IS NULL;
        UPDATE public.metodos_pago SET sucursal_id = destino WHERE sucursal_id IS NULL;
    ELSE
        DELETE FROM public.extras       WHERE sucursal_id IS NULL;
        DELETE FROM public.tipos_evento WHERE sucursal_id IS NULL;
        DELETE FROM public.metodos_pago WHERE sucursal_id IS NULL;
    END IF;
END $$;

ALTER TABLE public.extras ALTER COLUMN sucursal_id SET NOT NULL;
ALTER TABLE public.tipos_evento ALTER COLUMN sucursal_id SET NOT NULL;
ALTER TABLE public.metodos_pago ALTER COLUMN sucursal_id SET NOT NULL;

-- Ya no puede haber sucursal_id NULL, así que el índice parcial que
-- imponía unicidad "entre catálogos globales" queda sin objeto.
DROP INDEX IF EXISTS public.uq_tipos_evento_nombre_global;
DROP INDEX IF EXISTS public.uq_metodos_pago_nombre_global;
