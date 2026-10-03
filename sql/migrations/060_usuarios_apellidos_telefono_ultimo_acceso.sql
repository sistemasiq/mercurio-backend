-- 060_usuarios_apellidos_telefono_ultimo_acceso.sql
-- Datos adicionales de usuario para el formulario de Administración y el
-- registro de último acceso (se actualiza en el login).

ALTER TABLE public.usuarios
    ADD COLUMN IF NOT EXISTS apellidos VARCHAR(150) NULL,
    ADD COLUMN IF NOT EXISTS telefono VARCHAR(20) NULL,
    ADD COLUMN IF NOT EXISTS ultimo_acceso TIMESTAMPTZ NULL;
