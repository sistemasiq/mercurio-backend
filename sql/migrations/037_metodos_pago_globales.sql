-- =============================================================================
-- 037_metodos_pago_globales.sql
-- Reversa 034_quitar_alcance_global.sql específicamente para metodos_pago:
-- decisión de producto revisada -- los métodos de pago sí deben ser un
-- catálogo global (Efectivo/Tarjeta/Cupones/Lealtad/Otro), con activación
-- independiente por sucursal, en vez de que cada sucursal duplique su propia
-- fila. extras y tipos_evento NO cambian, siguen exclusivos por sucursal --
-- esa parte de la decisión de 034 se mantiene.
--
-- CORREGIDA tras el primer intento de aplicarla contra la BD compartida:
-- esa BD tiene estructura (políticas RLS, funciones app.*, y una FK desde
-- movimientos_caja) que no vive en ningún archivo de sql/migrations/ -- la
-- tocó alguien fuera de las migraciones del repo. Esta versión se ajusta a
-- ese estado real en vez de asumir solo lo que los archivos del repo dicen:
--   - Remapea también pagos_ordenes y movimientos_caja (no solo
--     pagos_reservacion/pagos_estancia, que era todo lo que existía en el
--     repo cuando se escribió la primera versión).
--   - sucursal_metodos_pago replica el patrón RLS + trigger de modificado
--     que ya usa metodos_pago y configuracion_lealtad en esa BD.
--   - Una misma sucursal puede tener MÁS DE UNA fila del mismo `tipo`
--     (pruebas, ediciones -- ej. Puebla Angelópolis con "Efectivo" inactivo
--     y "Efectivo1" activo). Se usa el estado `activo` de la fila más
--     reciente de esa sucursal para ese tipo, no un JOIN directo que
--     pisaría el resultado de forma no determinística.
--
-- Consolidación: por cada `tipo` se conserva UNA fila canónica (la más
-- antigua). Los pagos históricos que referenciaban una fila duplicada se
-- remapean a la canónica antes de borrar los duplicados -- no se pierde
-- ningún registro.
--
-- Activación por sucursal: nueva tabla sucursal_metodos_pago. Para cada
-- sucursal que ya tenía al menos una fila de un tipo dado, se conserva el
-- `activo` de su fila más reciente de ese tipo. Para sucursales que nunca
-- configuraron ese tipo, se activa por default (mejor sobra un método
-- disponible que faltar uno que ya se usaba).
-- =============================================================================

BEGIN;

-- 1. Fila canónica por tipo (la más antigua).
CREATE TEMP TABLE _canonico AS
SELECT DISTINCT ON (tipo) tipo, id AS canonico_id
FROM metodos_pago
ORDER BY tipo, creado ASC, id ASC;

-- 2. Remapear pagos históricos de cada duplicado a su canónica -- las 4
--    tablas que hoy referencian metodos_pago.id en la BD real (verificado
--    vía information_schema, no asumido de los archivos del repo).
UPDATE pagos_reservacion pr
SET metodo_pago_id = c.canonico_id
FROM metodos_pago mp
JOIN _canonico c ON c.tipo = mp.tipo
WHERE pr.metodo_pago_id = mp.id
  AND mp.id <> c.canonico_id;

UPDATE pagos_ordenes po
SET metodo_pago_id = c.canonico_id
FROM metodos_pago mp
JOIN _canonico c ON c.tipo = mp.tipo
WHERE po.metodo_pago_id = mp.id
  AND mp.id <> c.canonico_id;

UPDATE pagos_estancia pe
SET metodos_pago_id = c.canonico_id
FROM metodos_pago mp
JOIN _canonico c ON c.tipo = mp.tipo
WHERE pe.metodos_pago_id = mp.id
  AND mp.id <> c.canonico_id;

UPDATE movimientos_caja mc
SET metodo_pago_id = c.canonico_id
FROM metodos_pago mp
JOIN _canonico c ON c.tipo = mp.tipo
WHERE mc.metodo_pago_id = mp.id
  AND mp.id <> c.canonico_id;

-- 3. Tabla de activación por sucursal -- mismo patrón que
--    configuracion_lealtad (FK a usuarios en las columnas de auditoría,
--    ON DELETE CASCADE si se borra la sucursal).
CREATE TABLE IF NOT EXISTS public.sucursal_metodos_pago (
    sucursal_id    UUID NOT NULL REFERENCES public.sucursales(id) ON DELETE CASCADE,
    metodo_pago_id UUID NOT NULL REFERENCES public.metodos_pago(id),
    activo         BOOLEAN NOT NULL DEFAULT TRUE,
    creado         TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por     UUID REFERENCES public.usuarios(id) ON DELETE SET NULL,
    modificado     TIMESTAMPTZ DEFAULT now(),
    modificado_por UUID REFERENCES public.usuarios(id) ON DELETE SET NULL,
    PRIMARY KEY (sucursal_id, metodo_pago_id)
);

ALTER TABLE public.sucursal_metodos_pago ENABLE ROW LEVEL SECURITY;

-- Mismo patrón que metodos_pago: cualquiera lee; para escribir, admin o
-- alguien de la propia sucursal (activar/desactivar es decisión de cada
-- sucursal, no solo de admin -- a diferencia del catálogo global en sí).
CREATE POLICY sucursal_metodos_pago_select ON public.sucursal_metodos_pago
    FOR SELECT USING (true);

CREATE POLICY sucursal_metodos_pago_write ON public.sucursal_metodos_pago
    FOR ALL
    USING (app.usuario_tiene_rol(ARRAY['admin']) OR app.usuario_en_sucursal(sucursal_id))
    WITH CHECK (app.usuario_tiene_rol(ARRAY['admin']) OR app.usuario_en_sucursal(sucursal_id));

CREATE TRIGGER trg_sucursal_metodos_pago_modificado
    BEFORE UPDATE ON public.sucursal_metodos_pago
    FOR EACH ROW EXECUTE FUNCTION app.set_modificado();

-- Estado real más reciente por (sucursal, tipo) -- una sucursal puede tener
-- varias filas del mismo tipo (pruebas, ediciones); se usa la más nueva en
-- vez de un JOIN directo, que pisaría el resultado sin orden determinado
-- cuando hay más de una fila del mismo tipo en la misma sucursal.
CREATE TEMP TABLE _estado_sucursal_tipo AS
SELECT DISTINCT ON (sucursal_id, tipo) sucursal_id, tipo, activo
FROM metodos_pago
ORDER BY sucursal_id, tipo, creado DESC, id DESC;

-- Sucursales que ya tenían al menos una fila de este tipo: conservan el
-- activo de su fila más reciente de ese tipo.
INSERT INTO sucursal_metodos_pago (sucursal_id, metodo_pago_id, activo)
SELECT est.sucursal_id, c.canonico_id, est.activo
FROM _estado_sucursal_tipo est
JOIN _canonico c ON c.tipo = est.tipo
ON CONFLICT (sucursal_id, metodo_pago_id) DO NOTHING;

-- Sucursales que nunca configuraron ese tipo: se activa por default.
INSERT INTO sucursal_metodos_pago (sucursal_id, metodo_pago_id, activo)
SELECT s.id, c.canonico_id, TRUE
FROM sucursales s
CROSS JOIN _canonico c
ON CONFLICT (sucursal_id, metodo_pago_id) DO NOTHING;

-- 4. Borrar duplicados (ya sin referencias) y dejar metodos_pago global.
DELETE FROM metodos_pago mp
USING _canonico c
WHERE c.tipo = mp.tipo AND mp.id <> c.canonico_id;

ALTER TABLE public.metodos_pago DROP CONSTRAINT IF EXISTS metodos_pago_sucursal_id_fkey;
DROP INDEX IF EXISTS public.uq_metodos_pago_nombre_sucursal;
ALTER TABLE public.metodos_pago DROP COLUMN IF EXISTS sucursal_id;
-- El "activo" global queda obsoleto -- la activación real ahora vive por
-- sucursal en sucursal_metodos_pago. Se quita para que no queden dos
-- columnas con el mismo nombre y significados distintos.
ALTER TABLE public.metodos_pago DROP COLUMN IF EXISTS activo;
ALTER TABLE public.metodos_pago ADD CONSTRAINT uq_metodos_pago_tipo UNIQUE (tipo);

-- 5. Nombres canónicos legibles (la fila que sobrevivió pudo tener un
--    nombre libre raro, ej. "Efectivo Angelópolis").
UPDATE metodos_pago SET nombre = 'Efectivo' WHERE tipo = 'E';
UPDATE metodos_pago SET nombre = 'Tarjeta'  WHERE tipo = 'T';
UPDATE metodos_pago SET nombre = 'Cupones'  WHERE tipo = 'C';
UPDATE metodos_pago SET nombre = 'Lealtad'  WHERE tipo = 'L';
UPDATE metodos_pago SET nombre = 'Otro'     WHERE tipo = 'O';

-- 6. Asegurar que existan las 5 filas fijas aunque ninguna sucursal haya
--    creado nunca alguna de ellas, y activarla por default para todas.
INSERT INTO metodos_pago (nombre, tipo)
SELECT v.nombre, v.tipo
FROM (VALUES ('Efectivo', 'E'), ('Tarjeta', 'T'), ('Cupones', 'C'), ('Lealtad', 'L'), ('Otro', 'O'))
    AS v(nombre, tipo)
WHERE NOT EXISTS (SELECT 1 FROM metodos_pago mp WHERE mp.tipo = v.tipo);

INSERT INTO sucursal_metodos_pago (sucursal_id, metodo_pago_id, activo)
SELECT s.id, mp.id, TRUE
FROM sucursales s
CROSS JOIN metodos_pago mp
ON CONFLICT (sucursal_id, metodo_pago_id) DO NOTHING;

COMMIT;
