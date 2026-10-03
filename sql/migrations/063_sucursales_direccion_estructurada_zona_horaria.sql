-- 063_sucursales_direccion_estructurada_zona_horaria.sql
-- Dirección estructurada (ciudad, estado, código postal) y zona horaria de la
-- sucursal. Se mantiene la columna `direccion` existente (calle y número).

ALTER TABLE public.sucursales
    ADD COLUMN IF NOT EXISTS ciudad VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS estado VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS codigo_postal VARCHAR(10) NULL,
    ADD COLUMN IF NOT EXISTS zona_horaria VARCHAR(50) NOT NULL DEFAULT 'America/Mexico_City';
