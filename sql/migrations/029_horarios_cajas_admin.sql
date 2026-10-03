-- 029_horarios_cajas_admin.sql
-- Agrega campos activo/numero a cajas y turnos, y registra los permisos
-- para los CRUDs administrativos de horarios y cajas.

-- ── 1. Columna activo en turnos ───────────────────────────────────────────────
ALTER TABLE public.turnos
    ADD COLUMN IF NOT EXISTS activo BOOLEAN NOT NULL DEFAULT TRUE;

-- ── 2. Columnas numero y activo en cajas ─────────────────────────────────────
ALTER TABLE public.cajas
    ADD COLUMN IF NOT EXISTS numero SMALLINT NOT NULL DEFAULT 0;

ALTER TABLE public.cajas
    ADD COLUMN IF NOT EXISTS activo BOOLEAN NOT NULL DEFAULT TRUE;

-- Asignar numero único por sucursal a filas existentes
UPDATE public.cajas c
SET numero = sub.rn::SMALLINT
FROM (
    SELECT id,
           ROW_NUMBER() OVER (PARTITION BY sucursal_id ORDER BY creado) AS rn
    FROM public.cajas
) sub
WHERE c.id = sub.id;

-- Índice único parcial: numero no puede repetirse dentro de una sucursal activa
CREATE UNIQUE INDEX IF NOT EXISTS uq_cajas_numero_sucursal_activo
    ON public.cajas(numero, sucursal_id)
    WHERE activo = TRUE;

-- ── 3. Permisos nuevos ────────────────────────────────────────────────────────
INSERT INTO public.permisos (codigo, nombre, modulo) VALUES
    ('horarios:listar',   'Ver la página de gestión de horarios', 'horarios'),
    ('horarios:crear',    'Crear horarios de trabajo',            'horarios'),
    ('horarios:editar',   'Editar horarios de trabajo',           'horarios'),
    ('horarios:eliminar', 'Eliminar horarios de trabajo',         'horarios'),
    ('cajas:editar',      'Editar datos de una caja física',      'cajas'),
    ('cajas:eliminar',    'Desactivar una caja física',           'cajas')
ON CONFLICT (codigo) DO NOTHING;

-- ── 4. Asignar a AdministradorSistema (id=1) ─────────────────────────────────
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 1, p.id
FROM public.permisos p
WHERE (p.modulo = 'horarios' OR p.codigo IN ('cajas:editar', 'cajas:eliminar'))
  AND NOT EXISTS (
    SELECT 1 FROM public.rol_permisos rp
    WHERE rp.rol_id = 1 AND rp.permiso_id = p.id
  );

-- ── 5. Asignar a Administrador de Sucursal (id=2) ────────────────────────────
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 2, p.id
FROM public.permisos p
WHERE p.codigo IN (
    'horarios:listar',
    'horarios:crear',
    'horarios:editar',
    'horarios:eliminar',
    'cajas:listar',
    'cajas:crear',
    'cajas:editar',
    'cajas:eliminar'
)
AND NOT EXISTS (
    SELECT 1 FROM public.rol_permisos rp
    WHERE rp.rol_id = 2 AND rp.permiso_id = p.id
);
