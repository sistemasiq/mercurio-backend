-- 021_permisos_corte_caja.sql
-- Permisos para el módulo de Cierre de Caja (cajas, turnos_caja, retiros_parciales).

INSERT INTO public.permisos (codigo, nombre, modulo) VALUES
    -- módulo: cajas
    ('cajas:listar',              'Listar cajas de la sucursal',              'cajas'),
    ('cajas:crear',               'Registrar una nueva caja física',          'cajas'),
    -- módulo: turnos_caja
    ('turnos_caja:abrir',         'Abrir turno de caja',                      'turnos_caja'),
    ('turnos_caja:ver_activo',    'Ver turno activo y catálogos',             'turnos_caja'),
    ('turnos_caja:conteo',        'Enviar conteo físico del cajero',          'turnos_caja'),
    ('turnos_caja:revision_admin','Autenticar administrador para el balance', 'turnos_caja'),
    ('turnos_caja:confirmar',     'Confirmar cierre definitivo del turno',    'turnos_caja'),
    ('turnos_caja:cancelar',      'Cancelar conteo y regresar a ABIERTA',     'turnos_caja'),
    ('turnos_caja:historial',     'Consultar historial de arqueos',           'turnos_caja'),
    -- módulo: retiros_parciales
    ('retiros_parciales:crear',   'Registrar retiro parcial de efectivo',     'retiros_parciales'),
    ('retiros_parciales:listar',  'Listar retiros parciales del turno',       'retiros_parciales');

-- ── AdministradorSistema (id=1): todo lo nuevo ────────────────────────────────
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 1, p.id
FROM public.permisos p
WHERE p.modulo IN ('cajas', 'turnos_caja', 'retiros_parciales')
  AND NOT EXISTS (
    SELECT 1 FROM public.rol_permisos rp WHERE rp.rol_id = 1 AND rp.permiso_id = p.id
  );

-- ── Administrador (id=2): gestión y supervisión ───────────────────────────────
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 2, p.id
FROM public.permisos p
WHERE p.codigo IN (
    'cajas:listar',
    'cajas:crear',
    'turnos_caja:ver_activo',
    'turnos_caja:revision_admin',
    'turnos_caja:confirmar',
    'turnos_caja:historial',
    'retiros_parciales:listar'
)
AND NOT EXISTS (
    SELECT 1 FROM public.rol_permisos rp WHERE rp.rol_id = 2 AND rp.permiso_id = p.id
);

-- ── Cajero (id=3): operación de caja ─────────────────────────────────────────
INSERT INTO public.rol_permisos (rol_id, permiso_id)
SELECT 3, p.id
FROM public.permisos p
WHERE p.codigo IN (
    'cajas:listar',
    'turnos_caja:abrir',
    'turnos_caja:ver_activo',
    'turnos_caja:conteo',
    'turnos_caja:cancelar',
    'retiros_parciales:crear',
    'retiros_parciales:listar'
)
AND NOT EXISTS (
    SELECT 1 FROM public.rol_permisos rp WHERE rp.rol_id = 3 AND rp.permiso_id = p.id
);
