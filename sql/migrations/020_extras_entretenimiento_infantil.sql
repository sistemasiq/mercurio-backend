-- =============================================================================
-- 020_extras_entretenimiento_infantil.sql
-- Refresca el catálogo de extras (servicios externos) con el mismo criterio
-- de la 019: los extras de prueba ("Pinata nueva", "Piñata") se desactivan
-- en vez de borrarse porque uno de ellos ya está referenciado por una
-- reservación (FK ON DELETE RESTRICT en reservacion_extras). Se inserta un
-- catálogo real acorde al tema del negocio (estancia de entretenimiento
-- infantil), como extras globales (sucursal_id NULL) para que estén
-- disponibles en todas las sucursales.
-- =============================================================================

-- 1. Desactivar extras de prueba anteriores
UPDATE public.extras SET activo = false WHERE activo = true;

-- 2. Nuevos extras (servicios externos), globales
INSERT INTO public.extras (sucursal_id, nombre, descripcion, precio, unidad)
SELECT NULL, ex.nombre, ex.descripcion, ex.precio, ex.unidad
FROM (VALUES
    ('Piñata Temática',        'Piñata personalizada con relleno de dulces y sorpresas.',                350.00, 'evento'),
    ('Show de Personajes',     'Presentación de 30 minutos con personajes infantiles en vivo.',           900.00, 'evento'),
    ('Pintacaritas',           'Estación de pintacaritas con diseños a elegir, hasta 2 horas.',           450.00, 'evento'),
    ('Algodón de Azúcar',      'Máquina de algodones de azúcar, un algodón por niño.',                     40.00, 'persona'),
    ('Mesa de Dulces',         'Mesa temática con dulces y postres para todos los invitados.',            650.00, 'evento'),
    ('Fotografía del Evento',  'Cobertura fotográfica profesional durante todo el evento.',                750.00, 'evento'),
    ('Hora Extra',             'Extiende la duración del evento por 60 minutos adicionales.',              500.00, 'hora'),
    ('Renta de Inflable',      'Inflable adicional para más diversión.',                                   950.00, 'evento')
) AS ex(nombre, descripcion, precio, unidad)
WHERE NOT EXISTS (
    SELECT 1 FROM public.extras e
    WHERE e.sucursal_id IS NULL AND e.nombre = ex.nombre AND e.activo = true
);
