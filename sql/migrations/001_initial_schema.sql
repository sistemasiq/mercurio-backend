-- 001_initial_schema.sql
-- Roles, usuarios, sucursales y la relación usuario <-> sucursal.
-- Refleja el esquema existente en la base de datos (idempotente).

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()

-- Roles con id numérico (smallint). Catálogo fijo.
CREATE TABLE IF NOT EXISTS public.roles (
    id          SMALLINT PRIMARY KEY,
    nombre      VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    activo      BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO public.roles (id, nombre) VALUES
    (1, 'AdministradorSistema'),
    (2, 'Administrador'),
    (3, 'Cajero'),
    (4, 'Cocina')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS public.usuarios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(150) NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    nombre_completo VARCHAR(200) NOT NULL,
    rol             SMALLINT NOT NULL REFERENCES public.roles(id),
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    creado          TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por      UUID,
    modificado      TIMESTAMPTZ NOT NULL DEFAULT now(),
    modificado_por  UUID
);

CREATE TABLE IF NOT EXISTS public.sucursales (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre             VARCHAR(150) NOT NULL,
    direccion          TEXT,
    telefono           VARCHAR(10),
    correo             VARCHAR(150),
    administrador_id   UUID,
    administrador_name VARCHAR(200),
    clave              VARCHAR(50),
    activo             BOOLEAN NOT NULL DEFAULT TRUE,
    creado             TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por         UUID,
    modificado         TIMESTAMPTZ NOT NULL DEFAULT now(),
    modificado_por     UUID
);

-- Asignación de sucursales a usuarios (Administrador: varias; Cajero/Cocina: una).
CREATE TABLE IF NOT EXISTS public.usuarios_sucursal (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id     UUID NOT NULL REFERENCES public.usuarios(id),
    sucursal_id    UUID NOT NULL REFERENCES public.sucursales(id),
    activo         BOOLEAN NOT NULL DEFAULT TRUE,
    creado         TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por     UUID,
    modificado     TIMESTAMPTZ NOT NULL DEFAULT now(),
    modificado_por UUID
);
