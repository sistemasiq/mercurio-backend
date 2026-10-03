-- =============================================================================
-- 027_presentaciones_insumo.sql
-- Fase 7 de inventario: presentaciones de compra específicas de un insumo
-- (ej. "Paquete (8 pz)" de pan de hamburguesa), a diferencia de
-- unidades_medida que es un catálogo global con conversión universal
-- (1 kg siempre son 1000 g). equivalencia_base está expresada directo en
-- insumos.unidad_base_id del insumo dueño, sin pasar por unidades_medida.
--
-- detalle_compras pasa a aceptar unidad_medida_id O presentacion_id
-- (nunca ambos, nunca ninguno) para poder registrar una línea de compra
-- usando cualquiera de los dos caminos.
-- =============================================================================

CREATE TABLE public.presentaciones_insumo (
    id                UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    insumo_id         UUID           NOT NULL REFERENCES public.insumos(id),
    nombre            VARCHAR(100)   NOT NULL,
    equivalencia_base NUMERIC(12, 3) NOT NULL CHECK (equivalencia_base > 0),

    activo            BOOLEAN     NOT NULL DEFAULT TRUE,
    creado            TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por        UUID        REFERENCES public.usuarios(id),
    modificado        TIMESTAMPTZ DEFAULT now(),
    modificado_por    UUID        REFERENCES public.usuarios(id)
);

CREATE INDEX idx_presentaciones_insumo_insumo ON public.presentaciones_insumo (insumo_id);

ALTER TABLE public.detalle_compras
    ALTER COLUMN unidad_medida_id DROP NOT NULL,
    ADD COLUMN presentacion_id UUID REFERENCES public.presentaciones_insumo(id),
    ADD CONSTRAINT chk_detalle_compras_una_unidad CHECK (
        (unidad_medida_id IS NOT NULL)::int + (presentacion_id IS NOT NULL)::int = 1
    );
