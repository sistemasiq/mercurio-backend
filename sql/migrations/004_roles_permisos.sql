-- =============================================================================
-- 004_roles_permisos.sql
-- Introduce catálogo de roles, permisos y la tabla de asignación rol_permisos.
-- Migra usuarios.rol de ENUM (rol_tipo) a FK sobre la tabla roles.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. CATÁLOGO DE ROLES
--    Reemplaza al tipo ENUM rol_tipo.  Los 4 roles son fijos por ahora.
-- -----------------------------------------------------------------------------
CREATE TABLE public.roles (
    id          SMALLSERIAL  PRIMARY KEY,
    nombre      VARCHAR(50)  NOT NULL UNIQUE,
    descripcion TEXT,
    activo      BOOLEAN      NOT NULL DEFAULT TRUE
);

INSERT INTO public.roles (nombre, descripcion) VALUES
    ('AdministradorSistema', 'Acceso total al sistema sin restricción de sucursal.'),
    ('Administrador',        'Gestión completa de su sucursal asignada.'),
    ('Cajero',               'Operaciones de caja y punto de venta.'),
    ('Cocina',               'Gestión de órdenes y comandas de cocina.');

-- -----------------------------------------------------------------------------
-- 2. CATÁLOGO DE PERMISOS
-- -----------------------------------------------------------------------------
CREATE TABLE public.permisos (
    id          SERIAL        PRIMARY KEY,
    codigo      VARCHAR(100)  NOT NULL UNIQUE,
    nombre      VARCHAR(150)  NOT NULL,
    modulo      VARCHAR(50)   NOT NULL,
    descripcion TEXT
);

INSERT INTO public.permisos (codigo, nombre, modulo) VALUES
    -- módulo: usuarios
    ('usuarios:listar',                  'Listar usuarios',                    'usuarios'),
    ('usuarios:ver',                     'Ver detalle de usuario',             'usuarios'),
    ('usuarios:crear',                   'Crear usuarios',                     'usuarios'),
    ('usuarios:editar',                  'Editar usuarios',                    'usuarios'),
    ('usuarios:eliminar',                'Eliminar usuarios',                  'usuarios'),
    -- módulo: sucursales
    ('sucursales:listar',                'Listar sucursales',                  'sucursales'),
    ('sucursales:ver',                   'Ver detalle de sucursal',            'sucursales'),
    ('sucursales:crear',                 'Crear sucursales',                   'sucursales'),
    ('sucursales:editar',                'Editar sucursales',                  'sucursales'),
    ('sucursales:eliminar',              'Eliminar sucursales',                'sucursales'),
    -- módulo: pos
    ('pos:acceder',                      'Acceder al módulo POS',              'pos'),
    ('pos:abrir_turno',                  'Abrir turno de caja',                'pos'),
    ('pos:cerrar_turno',                 'Cerrar turno de caja',               'pos'),
    ('pos:ver_turnos',                   'Ver historial de turnos',            'pos'),
    -- módulo: inventario
    ('inventario:ver',                   'Ver inventario y stock',             'inventario'),
    ('inventario:gestionar_productos',   'Crear y editar productos',           'inventario'),
    ('inventario:eliminar_producto',     'Eliminar productos',                 'inventario'),
    ('inventario:registrar_movimiento',  'Registrar movimientos de stock',     'inventario'),
    ('inventario:gestionar_proveedores', 'Gestionar proveedores',              'inventario'),
    -- módulo: restaurante
    ('restaurante:ver_mesas',            'Ver estado de mesas',                'restaurante'),
    ('restaurante:gestionar_mesas',      'Configurar mesas',                   'restaurante'),
    ('restaurante:ver_menu',             'Ver menú',                           'restaurante'),
    ('restaurante:gestionar_menu',       'Crear y editar el menú',             'restaurante'),
    ('restaurante:ver_pedidos',          'Ver pedidos del turno',              'restaurante'),
    ('restaurante:crear_pedido',         'Tomar pedidos',                      'restaurante'),
    ('restaurante:editar_pedido',        'Modificar pedidos activos',          'restaurante'),
    ('restaurante:gestionar_cocina',     'Actualizar estado de comandas',      'restaurante'),
    -- módulo: reportes
    ('reportes:dashboard',               'Ver dashboard general',              'reportes'),
    ('reportes:ventas',                  'Ver reporte de ventas',              'reportes'),
    ('reportes:inventario',              'Ver reporte de inventario',          'reportes'),
    ('reportes:usuarios',                'Ver reporte de actividad de usuarios','reportes'),
    -- módulo: permisos
    ('permisos:ver',                     'Ver configuración de permisos',      'permisos'),
    ('permisos:editar',                  'Editar permisos de roles',           'permisos');

-- -----------------------------------------------------------------------------
-- 3. ASIGNACIÓN ROL → PERMISOS  (editable desde la UI)
-- -----------------------------------------------------------------------------
CREATE TABLE public.rol_permisos (
    rol_id     SMALLINT NOT NULL REFERENCES public.roles(id)   ON DELETE CASCADE,
    permiso_id INT      NOT NULL REFERENCES public.permisos(id) ON DELETE CASCADE,
    PRIMARY KEY (rol_id, permiso_id)
);

-- AdministradorSistema (id=1): todos los permisos
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 1, id FROM public.permisos;

-- Administrador (id=2)
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 2, id FROM public.permisos
WHERE codigo IN (
    'usuarios:listar', 'usuarios:ver', 'usuarios:crear', 'usuarios:editar', 'usuarios:eliminar',
    'sucursales:listar', 'sucursales:ver',
    'pos:acceder', 'pos:abrir_turno', 'pos:cerrar_turno', 'pos:ver_turnos',
    'inventario:ver', 'inventario:gestionar_productos', 'inventario:registrar_movimiento',
    'inventario:gestionar_proveedores',
    'restaurante:ver_mesas', 'restaurante:gestionar_mesas',
    'restaurante:ver_menu', 'restaurante:gestionar_menu',
    'restaurante:ver_pedidos', 'restaurante:crear_pedido',
    'restaurante:editar_pedido', 'restaurante:gestionar_cocina',
    'reportes:dashboard', 'reportes:ventas', 'reportes:inventario',
    'permisos:ver'
);

-- Cajero (id=3)
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 3, id FROM public.permisos
WHERE codigo IN (
    'pos:acceder', 'pos:abrir_turno', 'pos:cerrar_turno',
    'inventario:registrar_movimiento',
    'restaurante:ver_mesas', 'restaurante:ver_menu',
    'restaurante:ver_pedidos', 'restaurante:crear_pedido', 'restaurante:editar_pedido'
);

-- Cocina (id=4)
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 4, id FROM public.permisos
WHERE codigo IN (
    'restaurante:ver_mesas', 'restaurante:ver_menu',
    'restaurante:ver_pedidos', 'restaurante:gestionar_cocina'
);

-- -----------------------------------------------------------------------------
-- 4. MIGRAR usuarios.rol  de ENUM rol_tipo  →  FK a roles(id)
-- -----------------------------------------------------------------------------
-- 4.1  Columna temporal para guardar el nuevo ID de rol
ALTER TABLE public.usuarios ADD COLUMN rol_id SMALLINT;

-- 4.2  Poblar desde el catálogo de roles usando el texto del ENUM
UPDATE public.usuarios u
SET rol_id = r.id
FROM public.roles r
WHERE r.nombre = u.rol::TEXT;

-- 4.3  Forzar NOT NULL (todos los registros deben haber hecho match)
ALTER TABLE public.usuarios ALTER COLUMN rol_id SET NOT NULL;

-- 4.4  Sustituir la columna vieja por la nueva
ALTER TABLE public.usuarios DROP COLUMN rol;
ALTER TABLE public.usuarios RENAME COLUMN rol_id TO rol;

-- 4.5  Restricción de FK
ALTER TABLE public.usuarios
    ADD CONSTRAINT fk_usuarios_rol FOREIGN KEY (rol) REFERENCES public.roles(id);

-- 4.6  Eliminar el tipo ENUM (ya no lo usa nadie)
DROP TYPE public.rol_tipo;
