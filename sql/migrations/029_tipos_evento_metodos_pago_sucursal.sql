-- =============================================================================
-- 029_tipos_evento_metodos_pago_sucursal.sql
-- HALLAZGO-01: tipos_evento y metodos_pago eran catálogos 100% globales
-- (sin sucursal_id), a diferencia de extras que ya soporta el patrón
-- "NULL = global" (013_eventos_catalogos.sql). Los lleva al mismo patrón.
--
-- nombre era UNIQUE global en ambas tablas; con sucursal_id nullable eso ya
-- no alcanza: un UNIQUE(nombre, sucursal_id) simple no evita duplicados
-- "globales" (NULL <> NULL para Postgres), así que se agrega además un
-- índice único parcial que sí impone unicidad entre catálogos globales.
--
-- El DROP CONSTRAINT usa el nombre por defecto que Postgres asigna a un
-- UNIQUE inline declarado en CREATE TABLE (<tabla>_<columna>_key). Si al
-- aplicar esta migración el nombre real difiere, ajustarlo antes de correr.
-- =============================================================================

ALTER TABLE public.tipos_evento ADD COLUMN IF NOT EXISTS sucursal_id UUID REFERENCES public.sucursales(id);
ALTER TABLE public.tipos_evento DROP CONSTRAINT IF EXISTS tipos_evento_nombre_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_tipos_evento_nombre_sucursal ON public.tipos_evento (nombre, sucursal_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_tipos_evento_nombre_global ON public.tipos_evento (nombre) WHERE sucursal_id IS NULL;

ALTER TABLE public.metodos_pago ADD COLUMN IF NOT EXISTS sucursal_id UUID REFERENCES public.sucursales(id);
ALTER TABLE public.metodos_pago DROP CONSTRAINT IF EXISTS metodos_pago_nombre_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_metodos_pago_nombre_sucursal ON public.metodos_pago (nombre, sucursal_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_metodos_pago_nombre_global ON public.metodos_pago (nombre) WHERE sucursal_id IS NULL;
