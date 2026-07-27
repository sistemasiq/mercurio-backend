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
-- =============================================================================

UPDATE public.extras
SET sucursal_id = '1eb11d0c-8a9c-468d-bbc6-0e649e9bfcf2'
WHERE sucursal_id IS NULL;

UPDATE public.tipos_evento
SET sucursal_id = '1eb11d0c-8a9c-468d-bbc6-0e649e9bfcf2'
WHERE sucursal_id IS NULL;

UPDATE public.metodos_pago
SET sucursal_id = '1eb11d0c-8a9c-468d-bbc6-0e649e9bfcf2'
WHERE sucursal_id IS NULL;

ALTER TABLE public.extras ALTER COLUMN sucursal_id SET NOT NULL;
ALTER TABLE public.tipos_evento ALTER COLUMN sucursal_id SET NOT NULL;
ALTER TABLE public.metodos_pago ALTER COLUMN sucursal_id SET NOT NULL;

-- Ya no puede haber sucursal_id NULL, así que el índice parcial que
-- imponía unicidad "entre catálogos globales" queda sin objeto.
DROP INDEX IF EXISTS public.uq_tipos_evento_nombre_global;
DROP INDEX IF EXISTS public.uq_metodos_pago_nombre_global;
