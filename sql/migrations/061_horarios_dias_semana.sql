-- 061_horarios_dias_semana.sql
-- Días de la semana en los que aplica un horario (turno de trabajo).
-- 0 = lunes ... 6 = domingo; NULL = todos los días.

ALTER TABLE public.turnos
    ADD COLUMN IF NOT EXISTS dias SMALLINT[] NULL;
