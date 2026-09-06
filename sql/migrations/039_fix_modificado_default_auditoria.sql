-- =============================================================================
-- 039_fix_modificado_default_auditoria.sql
-- Bug (QA 2026-08-17): `modificado` se llenaba automáticamente en el INSERT
-- porque las columnas tenían DEFAULT now(), aunque ningún endpoint de
-- creación las incluye explícitamente en su lista de columnas. Esto rompe la
-- semántica esperada: modificado/modificado_por deben quedar NULL hasta que
-- exista una modificación real (la cual sí los establece explícitamente,
-- ver caja_repository.py y branch_repository.py).
--
-- apertura_caja ya se había corregido (su DEFAULT ya no existe en la BD
-- compartida), pero cajas, turnos y sucursales seguían con el DEFAULT.
-- Además, las cuatro tablas tienen filas históricas contaminadas por el
-- mismo bug: modificado con valor pero modificado_por NULL (ninguna
-- modificación real deja modificado_por en NULL), que se limpian aquí.
-- =============================================================================

ALTER TABLE public.cajas      ALTER COLUMN modificado DROP DEFAULT;
ALTER TABLE public.turnos     ALTER COLUMN modificado DROP DEFAULT;
ALTER TABLE public.sucursales ALTER COLUMN modificado DROP DEFAULT;

UPDATE public.cajas
SET modificado = NULL
WHERE modificado IS NOT NULL AND modificado_por IS NULL;

UPDATE public.turnos
SET modificado = NULL
WHERE modificado IS NOT NULL AND modificado_por IS NULL;

UPDATE public.sucursales
SET modificado = NULL
WHERE modificado IS NOT NULL AND modificado_por IS NULL;

UPDATE public.apertura_caja
SET modificado = NULL
WHERE modificado IS NOT NULL AND modificado_por IS NULL;
