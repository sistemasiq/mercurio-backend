-- =============================================================================
-- seed_local.sql
-- Datos mínimos para trabajar contra la BD local en Docker. NO se aplica nunca
-- a la BD compartida: sólo lo invoca ./scripts/reset_db_local.sh --seed.
--
-- Las migraciones ya siembran roles, permisos y tipos_evento; aquí sólo va lo
-- que falta para poder entrar a la app y ver el catálogo: una sucursal, los
-- usuarios de acceso, productos para "alimentos incluidos" y paquetes con
-- rangos de invitados escalonados que se solapan a propósito, para poder
-- comprobar el filtrado del asistente de reservación.
--
-- Contraseña de todos los usuarios: 12345678
-- =============================================================================

-- 1. Sucursal -----------------------------------------------------------------

INSERT INTO public.sucursales (id, nombre, direccion, telefono, correo, clave)
VALUES ('11111111-1111-1111-1111-111111111111',
        'Sucursal Local', 'Calle Falsa 123', '3310000000',
        'local@woowkids.dev', 'LOCAL')
ON CONFLICT (id) DO NOTHING;

-- 2. Usuarios -----------------------------------------------------------------
-- Hash bcrypt de '12345678', generado con app.core.security.hash_password.

INSERT INTO public.usuarios (id, email, password_hash, nombre_completo, rol)
VALUES
  ('22222222-2222-2222-2222-222222222222',
   'admin@local.dev',
   '$2b$12$jGOsFgnr5KIF6TB6gbQ7A.tDGDQ56EsXo8NhGA9oPBYOgAvGIGLWO',
   'Admin Local', 2),
  ('33333333-3333-3333-3333-333333333333',
   'sistemas@local.dev',
   '$2b$12$jGOsFgnr5KIF6TB6gbQ7A.tDGDQ56EsXo8NhGA9oPBYOgAvGIGLWO',
   'Administrador de Sistema Local', 1)
ON CONFLICT (id) DO NOTHING;

-- El rol Administrador (2) exige sucursal asignada; el AdministradorSistema (1)
-- va sin fila aquí a propósito, porque su acceso es global.
INSERT INTO public.usuarios_sucursal (usuario_id, sucursal_id)
VALUES ('22222222-2222-2222-2222-222222222222',
        '11111111-1111-1111-1111-111111111111')
ON CONFLICT (usuario_id, sucursal_id) DO NOTHING;

-- 3. Productos (para los alimentos incluidos del paquete) ----------------------

INSERT INTO public.productos (id, nombre, precio_unitario, tipo, sucursal_id)
VALUES
  ('aaaaaaaa-0000-0000-0000-000000000001', 'Rebanada de pizza',  35.00, 'A',
   '11111111-1111-1111-1111-111111111111'),
  ('aaaaaaaa-0000-0000-0000-000000000002', 'Refresco 355ml',     20.00, 'B',
   '11111111-1111-1111-1111-111111111111'),
  ('aaaaaaaa-0000-0000-0000-000000000003', 'Bolsa de palomitas', 25.00, 'A',
   '11111111-1111-1111-1111-111111111111')
ON CONFLICT (id) DO NOTHING;

-- 4. Paquetes con rangos escalonados ------------------------------------------
-- Los rangos se solapan a propósito para probar el filtro del asistente:
--     8 niños  -> sólo Pequeño
--    15 niños  -> Pequeño y Mediano
--    28 niños  -> Mediano y Grande
--    60 niños  -> ninguno (debe mostrar el mensaje de "sin paquetes")

INSERT INTO public.paquetes
    (id, sucursal_id, nombre, descripcion, min_invitados, max_invitados,
     precio_base, precio_pulsera)
VALUES
  ('bbbbbbbb-0000-0000-0000-000000000001',
   '11111111-1111-1111-1111-111111111111',
   'Paquete Pequeño', 'Ideal para fiestas íntimas', 5, 15, 2500.00, 120.00),
  ('bbbbbbbb-0000-0000-0000-000000000002',
   '11111111-1111-1111-1111-111111111111',
   'Paquete Mediano', 'El más contratado', 12, 30, 4200.00, 150.00),
  ('bbbbbbbb-0000-0000-0000-000000000003',
   '11111111-1111-1111-1111-111111111111',
   'Paquete Grande', 'Para grupos escolares', 25, 50, 7000.00, 180.00)
ON CONFLICT (id) DO NOTHING;

-- Alimentos incluidos en el paquete mediano
INSERT INTO public.paquete_productos (paquete_id, producto_id, cantidad)
VALUES
  ('bbbbbbbb-0000-0000-0000-000000000002',
   'aaaaaaaa-0000-0000-0000-000000000001', 12),
  ('bbbbbbbb-0000-0000-0000-000000000002',
   'aaaaaaaa-0000-0000-0000-000000000002', 12)
ON CONFLICT (paquete_id, producto_id) DO NOTHING;

-- Todos los paquetes sirven para cualquier tipo de evento sembrado
INSERT INTO public.paquete_tipos_evento (paquete_id, tipo_evento_id)
SELECT p.id, t.id
  FROM public.paquetes p
 CROSS JOIN public.tipos_evento t
 WHERE p.sucursal_id = '11111111-1111-1111-1111-111111111111'
ON CONFLICT (paquete_id, tipo_evento_id) DO NOTHING;
