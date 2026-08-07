-- =============================================================================
-- 034_paquetes_rango_invitados_pulsera.sql
-- Reemplaza el modelo de cobro "personas incluidas + persona extra + hora"
-- por "rango de invitados + pulsera por invitado".
--
-- Qué cambia y por qué:
--
-- 1. personas_incluidas -> min_invitados, + max_invitados (nuevo)
--    Un paquete ahora declara el rango de invitados que soporta. Sirve para
--    filtrar: en el paso 2 del asistente de reservación solo se muestran los
--    paquetes cuyo rango cubre el número de niños que el cliente pidió en el
--    paso 1. Antes personas_incluidas era un tope suelto ("Hasta N personas")
--    que no filtraba nada, solo disparaba el cobro de personas extra.
--
-- 2. precio_persona_extra -> precio_pulsera
--    Deja de ser un recargo por excedente y pasa a ser el precio de la pulsera
--    de cada invitado. Se cobra por TODOS los invitados del evento, no solo por
--    los que rebasan el mínimo:
--        total = precio_base + (precio_pulsera × número de invitados)
--
-- 3. Se elimina precio_hora
--    El cobro por hora desaparece del modelo de paquetes (lo introdujo
--    031_paquetes_precio_hora.sql). Las columnas horas_reservadas y
--    precio_horas de reservaciones NO se tocan: son fotos históricas de
--    eventos ya levantados y borrarlas perdería información contable. Las
--    reservaciones nuevas simplemente guardan precio_horas = 0, conservando
--    horas_reservadas porque la duración real del evento sigue siendo un dato
--    válido aunque ya no se cobre.
--
-- Relleno de los paquetes existentes: min_invitados = 1 y
-- max_invitados = personas_incluidas anterior. Así ningún paquete del catálogo
-- actual desaparece del asistente (todos aceptan desde 1 niño) y el tope que ya
-- se mostraba en la UI se conserva tal cual. El staff ajusta los mínimos reales
-- después desde la pantalla de paquetes.
-- =============================================================================

-- 1. Rango de invitados -------------------------------------------------------

ALTER TABLE public.paquetes
    RENAME COLUMN personas_incluidas TO min_invitados;

ALTER TABLE public.paquetes
    ADD COLUMN IF NOT EXISTS max_invitados INTEGER;

-- El valor viejo era un tope ("Hasta N personas"), así que se mueve a max_ y el
-- mínimo arranca en 1. Orden importante: primero se copia, luego se pisa min_.
UPDATE public.paquetes
   SET max_invitados = min_invitados
 WHERE max_invitados IS NULL;

UPDATE public.paquetes
   SET min_invitados = 1;

ALTER TABLE public.paquetes
    ALTER COLUMN max_invitados SET NOT NULL,
    ALTER COLUMN min_invitados SET DEFAULT 1,
    ALTER COLUMN max_invitados SET DEFAULT 10;

-- Un rango invertido (min > max) haría que el paquete nunca aparezca en el
-- asistente: se bloquea en la BD, no solo en el formulario.
ALTER TABLE public.paquetes
    DROP CONSTRAINT IF EXISTS chk_paquetes_rango_invitados;

ALTER TABLE public.paquetes
    ADD CONSTRAINT chk_paquetes_rango_invitados
    CHECK (min_invitados > 0 AND max_invitados >= min_invitados);

-- 2. Pulsera por invitado -----------------------------------------------------

ALTER TABLE public.paquetes
    RENAME COLUMN precio_persona_extra TO precio_pulsera;

-- 3. Fuera el cobro por hora --------------------------------------------------

ALTER TABLE public.paquetes
    DROP COLUMN IF EXISTS precio_hora;
