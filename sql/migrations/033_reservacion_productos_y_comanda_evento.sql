-- =============================================================================
-- 033_reservacion_productos_y_comanda_evento.sql
-- Productos ad-hoc por reservación (además de los ya incluidos en el
-- paquete vía paquete_productos), y el soporte para que un scheduler en el
-- backend arme automáticamente una comanda de cocina con esos alimentos
-- antes de que llegue la hora del evento:
--   - reservaciones.precio_productos: suma congelada de los productos
--     ad-hoc, paralela a precio_horas/precio_personas_extra (no se mezcla
--     con precio_extras, que sigue atada 1:1 a reservacion_extras).
--   - reservaciones.comanda_enviada: bandera de idempotencia para que el
--     scheduler no reprocese la misma reservación en cada ciclo.
--   - comandas.reservacion_id: para que cocina sepa que esa comanda es de
--     un evento, y para poder rastrearla.
--   - un usuario "Sistema" dedicado, usado como creado_por de las comandas
--     automáticas (crear_comanda exige un usuario real; no se reutiliza
--     una cuenta de admin real para no confundir la auditoría).
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.reservacion_productos (
    id              UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    reservacion_id  UUID           NOT NULL REFERENCES public.reservaciones(id),
    producto_id     UUID           NOT NULL REFERENCES public.productos(id),
    cantidad        INTEGER        NOT NULL,
    precio_unitario NUMERIC(10, 2) NOT NULL,
    subtotal        NUMERIC(10, 2) GENERATED ALWAYS AS (cantidad * precio_unitario) STORED,
    notas           TEXT,
    creado          TIMESTAMPTZ    NOT NULL DEFAULT now(),
    creado_por      UUID           REFERENCES public.usuarios(id)
);

ALTER TABLE public.reservaciones
    ADD COLUMN IF NOT EXISTS precio_productos NUMERIC(10, 2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS comanda_enviada  BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.comandas
    ADD COLUMN IF NOT EXISTS reservacion_id UUID NULL REFERENCES public.reservaciones(id);

-- Usuario "Sistema" para atribuir las comandas creadas automáticamente por
-- el scheduler. password_hash es un bcrypt de una contraseña aleatoria
-- desechada — esta cuenta nunca debe poder iniciar sesión.
INSERT INTO public.usuarios (id, email, password_hash, nombre_completo, activo, rol)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'sistema@mercury.internal',
    '$2b$12$1.UyHXPmALkBSPqgtfWzcunfWNDSfZpaRQiNC8fiCPy2VyNiEu6w6',
    'Sistema (comandas automáticas)',
    TRUE,
    1  -- AdministradorSistema
)
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.permisos (codigo, nombre, modulo) VALUES
    ('reservaciones:gestionar_productos', 'Gestionar productos ad-hoc de una reservación', 'reservaciones')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM public.roles r
CROSS JOIN public.permisos p
WHERE r.id IN (1, 2, 3) AND p.codigo = 'reservaciones:gestionar_productos'
ON CONFLICT DO NOTHING;
