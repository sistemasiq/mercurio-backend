-- =============================================================================
-- 037_metodos_pago_globales.sql
-- Reversa 034_quitar_alcance_global.sql específicamente para metodos_pago:
-- decisión de producto revisada -- los métodos de pago sí deben ser un
-- catálogo global (Efectivo/Tarjeta/Cupones/Lealtad/Otro), con activación
-- independiente por sucursal, en vez de que cada sucursal duplique su propia
-- fila. extras y tipos_evento NO cambian, siguen exclusivos por sucursal --
-- esa parte de la decisión de 034 se mantiene.
--
-- Consolidación: por cada `tipo` se conserva UNA fila canónica (la más
-- antigua). Los pagos históricos en pagos_reservacion/pagos_estancia que
-- referenciaban una fila duplicada se remapean a la canónica antes de borrar
-- los duplicados -- no se pierde ningún registro.
--
-- Activación por sucursal: nueva tabla sucursal_metodos_pago. Para cada
-- sucursal que ya tenía una fila de un tipo dado, se conserva su `activo`
-- tal cual. Para sucursales que nunca configuraron ese tipo, se activa por
-- default (mejor sobra un método disponible que faltar uno que ya se usaba).
-- =============================================================================

-- 1. Fila canónica por tipo (la más antigua).
CREATE TEMP TABLE _canonico AS
SELECT DISTINCT ON (tipo) tipo, id AS canonico_id
FROM metodos_pago
ORDER BY tipo, creado ASC, id ASC;

-- 2. Remapear pagos históricos de cada duplicado a su canónica.
UPDATE pagos_reservacion pr
SET metodo_pago_id = c.canonico_id
FROM metodos_pago mp
JOIN _canonico c ON c.tipo = mp.tipo
WHERE pr.metodo_pago_id = mp.id
  AND mp.id <> c.canonico_id;

UPDATE pagos_estancia pe
SET metodos_pago_id = c.canonico_id
FROM metodos_pago mp
JOIN _canonico c ON c.tipo = mp.tipo
WHERE pe.metodos_pago_id = mp.id
  AND mp.id <> c.canonico_id;

-- 3. Tabla de activación por sucursal.
CREATE TABLE IF NOT EXISTS public.sucursal_metodos_pago (
    sucursal_id    UUID NOT NULL REFERENCES public.sucursales(id),
    metodo_pago_id UUID NOT NULL REFERENCES public.metodos_pago(id),
    activo         BOOLEAN NOT NULL DEFAULT TRUE,
    creado         TIMESTAMPTZ NOT NULL DEFAULT now(),
    modificado     TIMESTAMPTZ DEFAULT now(),
    modificado_por UUID,
    PRIMARY KEY (sucursal_id, metodo_pago_id)
);

-- Sucursales que ya tenían una fila de este tipo: conservan su estado activo.
INSERT INTO sucursal_metodos_pago (sucursal_id, metodo_pago_id, activo)
SELECT mp.sucursal_id, c.canonico_id, mp.activo
FROM metodos_pago mp
JOIN _canonico c ON c.tipo = mp.tipo
ON CONFLICT (sucursal_id, metodo_pago_id) DO UPDATE SET activo = EXCLUDED.activo;

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
