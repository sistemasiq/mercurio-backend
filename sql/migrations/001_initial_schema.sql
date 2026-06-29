-- =============================================================================
-- 001_initial_schema.sql
-- Esquema inicial: usuarios, sucursales y asignación usuario-sucursal.
-- Orden de creación: usuarios → sucursales → usuarios_sucursal
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TIPO: roles del sistema
-- -----------------------------------------------------------------------------
CREATE TYPE public.rol_tipo AS ENUM (
    'AdministradorSistema',
    'Administrador',
    'Cajero',
    'Cocina'
);

-- -----------------------------------------------------------------------------
-- 1. USUARIOS
--    Tabla base de identidad y autenticación.
--    AdministradorSistema: sin entradas en usuarios_sucursal (acceso global).
--    Administrador:        1 o más entradas en usuarios_sucursal.
--    Cajero / Cocina:      exactamente 1 entrada en usuarios_sucursal.
-- -----------------------------------------------------------------------------
CREATE TABLE public.usuarios (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(254) NOT NULL,
    password_hash   TEXT         NOT NULL,
    nombre_completo VARCHAR(200) NOT NULL,
    rol             rol_tipo     NOT NULL,

    -- Auditoría
    activo         BOOLEAN     NOT NULL DEFAULT TRUE,
    creado         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creado_por     UUID        REFERENCES public.usuarios(id) ON DELETE SET NULL,
    modificado     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    modificado_por UUID        REFERENCES public.usuarios(id) ON DELETE SET NULL,

    CONSTRAINT uq_usuarios_email UNIQUE (email)
);

CREATE INDEX idx_usuarios_email_activo ON public.usuarios (email) WHERE activo = TRUE;

-- -----------------------------------------------------------------------------
-- 2. SUCURSALES
-- -----------------------------------------------------------------------------
CREATE TABLE public.sucursales (
    id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre         VARCHAR(150) NOT NULL,
    direccion      TEXT,
    telefono       VARCHAR(20),

    -- Auditoría
    activo         BOOLEAN     NOT NULL DEFAULT TRUE,
    creado         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creado_por     UUID        REFERENCES public.usuarios(id) ON DELETE SET NULL,
    modificado     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    modificado_por UUID        REFERENCES public.usuarios(id) ON DELETE SET NULL
);

-- -----------------------------------------------------------------------------
-- 3. USUARIOS_SUCURSAL
--    Tabla de asignación: qué sucursales puede operar cada usuario.
--    El rol vive en usuarios; aquí solo se registra el acceso.
-- -----------------------------------------------------------------------------
CREATE TABLE public.usuarios_sucursal (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id     UUID        NOT NULL REFERENCES public.usuarios(id)   ON DELETE CASCADE,
    sucursal_id    UUID        NOT NULL REFERENCES public.sucursales(id) ON DELETE CASCADE,

    -- Auditoría
    activo         BOOLEAN     NOT NULL DEFAULT TRUE,
    creado         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creado_por     UUID        REFERENCES public.usuarios(id) ON DELETE SET NULL,
    modificado     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    modificado_por UUID        REFERENCES public.usuarios(id) ON DELETE SET NULL,

    CONSTRAINT uq_usuario_sucursal UNIQUE (usuario_id, sucursal_id)
);

CREATE INDEX idx_us_usuario_id   ON public.usuarios_sucursal (usuario_id);
CREATE INDEX idx_us_sucursal_id  ON public.usuarios_sucursal (sucursal_id);
