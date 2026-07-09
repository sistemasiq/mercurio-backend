-- =============================================================================
-- 006_permisos_eventos_estancias.sql
--
-- 1) Restaura los permisos de pos/inventario/restaurante/reportes que la
--    migración 005 había eliminado por "no tener endpoints implementados".
--    Hoy sí existen (comandas.py, productos.py), así que esa premisa ya no
--    aplica. Se reinsertan con las mismas asignaciones de rol de la 004.
-- 2) Agrega el catálogo de permisos para el dominio eventos (reservaciones,
--    paquetes, tipos_evento, metodos_pago, extras) y para estancias
--    (registro de infantes / check-in), que nunca tuvieron permisos.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. RESTAURAR pos / inventario / restaurante / reportes
-- -----------------------------------------------------------------------------
INSERT INTO public.permisos (codigo, nombre, modulo) VALUES
    ('pos:acceder',                      'Acceder al módulo POS',              'pos'),
    ('pos:abrir_turno',                  'Abrir turno de caja',                'pos'),
    ('pos:cerrar_turno',                 'Cerrar turno de caja',                'pos'),
    ('pos:ver_turnos',                   'Ver historial de turnos',            'pos'),
    ('inventario:ver',                   'Ver inventario y stock',             'inventario'),
    ('inventario:gestionar_productos',   'Crear y editar productos',           'inventario'),
    ('inventario:eliminar_producto',     'Eliminar productos',                 'inventario'),
    ('inventario:registrar_movimiento',  'Registrar movimientos de stock',     'inventario'),
    ('inventario:gestionar_proveedores', 'Gestionar proveedores',              'inventario'),
    ('restaurante:ver_mesas',            'Ver estado de mesas',                'restaurante'),
    ('restaurante:gestionar_mesas',      'Configurar mesas',                   'restaurante'),
    ('restaurante:ver_menu',             'Ver menú',                           'restaurante'),
    ('restaurante:gestionar_menu',       'Crear y editar el menú',             'restaurante'),
    ('restaurante:ver_pedidos',          'Ver pedidos del turno',              'restaurante'),
    ('restaurante:crear_pedido',         'Tomar pedidos',                      'restaurante'),
    ('restaurante:editar_pedido',        'Modificar pedidos activos',          'restaurante'),
    ('restaurante:gestionar_cocina',     'Actualizar estado de comandas',      'restaurante'),
    ('reportes:dashboard',               'Ver dashboard general',              'reportes'),
    ('reportes:ventas',                  'Ver reporte de ventas',              'reportes'),
    ('reportes:inventario',              'Ver reporte de inventario',          'reportes'),
    ('reportes:usuarios',                'Ver reporte de actividad de usuarios','reportes');

-- Administrador (id=2)
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 2, id FROM public.permisos
WHERE codigo IN (
    'pos:acceder', 'pos:abrir_turno', 'pos:cerrar_turno', 'pos:ver_turnos',
    'inventario:ver', 'inventario:gestionar_productos', 'inventario:registrar_movimiento',
    'inventario:gestionar_proveedores',
    'restaurante:ver_mesas', 'restaurante:gestionar_mesas',
    'restaurante:ver_menu', 'restaurante:gestionar_menu',
    'restaurante:ver_pedidos', 'restaurante:crear_pedido',
    'restaurante:editar_pedido', 'restaurante:gestionar_cocina',
    'reportes:dashboard', 'reportes:ventas', 'reportes:inventario'
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
-- 2. NUEVO catálogo: eventos (reservaciones + catálogos) y estancias
-- -----------------------------------------------------------------------------
INSERT INTO public.permisos (codigo, nombre, modulo) VALUES
    -- módulo: reservaciones (incluye sub-recursos pagos_reservacion y reservacion_extras,
    -- que no tienen pantalla propia — se editan desde el detalle de una reservación)
    ('reservaciones:listar',            'Listar reservaciones',                'reservaciones'),
    ('reservaciones:ver',               'Ver detalle de reservación',          'reservaciones'),
    ('reservaciones:crear',             'Crear reservaciones',                 'reservaciones'),
    ('reservaciones:editar',            'Editar reservaciones',                'reservaciones'),
    ('reservaciones:eliminar',          'Eliminar reservaciones',              'reservaciones'),
    ('reservaciones:gestionar_pagos',   'Gestionar pagos de una reservación',  'reservaciones'),
    ('reservaciones:gestionar_extras',  'Gestionar extras de una reservación', 'reservaciones'),
    -- módulo: paquetes (incluye la relación paquete↔tipo_evento)
    ('paquetes:listar',                 'Listar paquetes',                     'paquetes'),
    ('paquetes:ver',                    'Ver detalle de paquete',              'paquetes'),
    ('paquetes:crear',                  'Crear paquetes',                      'paquetes'),
    ('paquetes:editar',                 'Editar paquetes',                     'paquetes'),
    ('paquetes:eliminar',               'Eliminar paquetes',                   'paquetes'),
    -- módulo: tipos_evento
    ('tipos_evento:listar',             'Listar tipos de evento',              'tipos_evento'),
    ('tipos_evento:ver',                'Ver detalle de tipo de evento',       'tipos_evento'),
    ('tipos_evento:crear',              'Crear tipos de evento',               'tipos_evento'),
    ('tipos_evento:editar',             'Editar tipos de evento',              'tipos_evento'),
    ('tipos_evento:eliminar',           'Eliminar tipos de evento',            'tipos_evento'),
    -- módulo: metodos_pago
    ('metodos_pago:listar',             'Listar métodos de pago',              'metodos_pago'),
    ('metodos_pago:ver',                'Ver detalle de método de pago',       'metodos_pago'),
    ('metodos_pago:crear',              'Crear métodos de pago',               'metodos_pago'),
    ('metodos_pago:editar',             'Editar métodos de pago',              'metodos_pago'),
    ('metodos_pago:eliminar',           'Eliminar métodos de pago',            'metodos_pago'),
    -- módulo: extras
    ('extras:listar',                   'Listar extras',                       'extras'),
    ('extras:ver',                      'Ver detalle de extra',                'extras'),
    ('extras:crear',                    'Crear extras',                        'extras'),
    ('extras:editar',                   'Editar extras',                       'extras'),
    ('extras:eliminar',                 'Eliminar extras',                     'extras'),
    -- módulo: estancias (registro de infantes / check-in)
    ('estancias:ver_activos',           'Ver niños en estancia activa',        'estancias'),
    ('estancias:checkin',               'Registrar entrada de niños',          'estancias'),
    ('estancias:checkout',              'Registrar salida de niños',           'estancias'),
    ('estancias:gestionar_pagos',       'Registrar pagos extra de estancia',   'estancias');

-- AdministradorSistema (id=1): recibe todo lo nuevo que aún no tenga
-- (incluye lo restaurado de la sección 1 y lo agregado en esta sección)
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 1, p.id
FROM public.permisos p
WHERE NOT EXISTS (
    SELECT 1 FROM public.rol_permisos rp WHERE rp.rol_id = 1 AND rp.permiso_id = p.id
);

-- Administrador (id=2): CRUD completo de eventos y estancias
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 2, id FROM public.permisos
WHERE modulo IN ('reservaciones', 'paquetes', 'tipos_evento', 'metodos_pago', 'extras', 'estancias');

-- Cajero (id=3): opera reservaciones y estancias (sin eliminar reservaciones),
-- solo consulta los catálogos de paquetes/tipos_evento/metodos_pago/extras
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 3, id FROM public.permisos
WHERE codigo IN (
    'reservaciones:listar', 'reservaciones:ver', 'reservaciones:crear',
    'reservaciones:editar', 'reservaciones:gestionar_pagos', 'reservaciones:gestionar_extras',
    'estancias:ver_activos', 'estancias:checkin', 'estancias:checkout', 'estancias:gestionar_pagos',
    'paquetes:listar', 'paquetes:ver',
    'tipos_evento:listar', 'tipos_evento:ver',
    'metodos_pago:listar', 'metodos_pago:ver',
    'extras:listar', 'extras:ver'
);

-- Cocina (id=4): sin acceso a eventos ni estancias.
