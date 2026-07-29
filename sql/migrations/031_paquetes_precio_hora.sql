-- =============================================================================
-- 031_paquetes_precio_hora.sql
-- Agrega precio por hora a los paquetes de evento (paquetes más grandes
-- pueden tener una tarifa/hora más baja, decisión manual del staff al
-- crear el paquete) y la posibilidad de declarar alimentos/bebidas
-- incluidos en el paquete, reutilizando el catálogo de productos.
--
-- El precio de una reservación pasa a sumar precio_base (fijo) +
-- (precio_hora del paquete × horas reservadas), calculado y congelado en
-- el cliente al momento de reservar (mismo patrón que ya existe hoy con
-- precio_base/precio_total) — de ahí las columnas nuevas en reservaciones.
-- =============================================================================

ALTER TABLE public.paquetes
    ADD COLUMN IF NOT EXISTS precio_hora NUMERIC(10, 2) NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS public.paquete_productos (
    id              UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    paquete_id      UUID           NOT NULL REFERENCES public.paquetes(id) ON DELETE CASCADE,
    producto_id     UUID           NOT NULL REFERENCES public.productos(id),
    cantidad        INTEGER        NOT NULL DEFAULT 1,

    activo          BOOLEAN     NOT NULL DEFAULT TRUE,
    creado          TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por      UUID        REFERENCES public.usuarios(id),
    modificado      TIMESTAMPTZ DEFAULT now(),
    modificado_por  UUID        REFERENCES public.usuarios(id),

    UNIQUE (paquete_id, producto_id)
);

CREATE INDEX IF NOT EXISTS idx_paquete_productos_paquete ON public.paquete_productos (paquete_id);

-- Congelados al reservar: horas_reservadas es lo que el cliente eligió en
-- el paso 1 del asistente de reservación; precio_horas es
-- paquete.precio_hora × horas_reservadas en ese momento. No se recalculan
-- después aunque cambie el precio_hora del paquete (igual que precio_base).
ALTER TABLE public.reservaciones
    ADD COLUMN IF NOT EXISTS horas_reservadas INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS precio_horas NUMERIC(10, 2) NOT NULL DEFAULT 0;
