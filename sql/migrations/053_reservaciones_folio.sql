-- =============================================================================
-- 053_reservaciones_folio.sql
-- Folio legible de reservación (p. ej. R-0418), secuencial global con prefijo.
-- Backfill de las reservaciones existentes en orden de creación (`creado`).
-- =============================================================================

CREATE SEQUENCE IF NOT EXISTS public.reservaciones_folio_seq;

ALTER TABLE public.reservaciones
    ADD COLUMN IF NOT EXISTS folio VARCHAR(20) UNIQUE;

-- Backfill determinista: el número de folio es la posición de la reservación
-- en orden de creación, no nextval() (su orden de evaluación por fila no está
-- garantizado en un UPDATE ... FROM con varias filas).
WITH ordenadas AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY creado) AS rn
    FROM public.reservaciones
    WHERE folio IS NULL
)
UPDATE public.reservaciones r
SET folio = 'R-' || LPAD(o.rn::text, 4, '0')
FROM ordenadas o
WHERE r.id = o.id;

-- La secuencia continúa después del folio más alto ya asignado, para que la
-- siguiente reservación creada por la aplicación (nextval) no choque con el
-- backfill.
SELECT setval(
    'public.reservaciones_folio_seq',
    COALESCE(
        (SELECT MAX(SUBSTRING(folio FROM 3)::int) FROM public.reservaciones WHERE folio ~ '^R-\d+$'),
        0
    )
);
