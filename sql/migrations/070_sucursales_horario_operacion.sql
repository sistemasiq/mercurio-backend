-- 070_sucursales_horario_operacion.sql
-- Horario de operación por sucursal. Con estos defaults el comportamiento
-- actual (horario fijo 09:00-23:00 en app/services/disponibilidad.py) no
-- cambia hasta que se edite la sucursal.

ALTER TABLE public.sucursales
    ADD COLUMN IF NOT EXISTS hora_apertura TIME NOT NULL DEFAULT '09:00',
    ADD COLUMN IF NOT EXISTS hora_cierre TIME NOT NULL DEFAULT '23:00';
