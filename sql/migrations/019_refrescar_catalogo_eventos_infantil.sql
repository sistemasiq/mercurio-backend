-- =============================================================================
-- 019_refrescar_catalogo_eventos_infantil.sql
-- Los tipos_evento y paquetes cargados hasta ahora eran datos de prueba
-- ("Cumpleanos jjj", "Cumpleanos modificado", "Paquete Basico NUEVO", etc.)
-- y siguen referenciados por reservaciones existentes (FK ON DELETE RESTRICT),
-- así que no se pueden borrar sin antes borrar esas reservaciones. Se
-- desactivan en vez de eliminarse, y se inserta el catálogo real acorde al
-- tema del negocio: una estancia de entretenimiento infantil (fiestas y
-- eventos para niños).
-- =============================================================================

-- 1. Desactivar catálogo de prueba anterior
UPDATE public.tipos_evento SET activo = false WHERE activo = true;
UPDATE public.paquetes SET activo = false WHERE activo = true;

-- 2. Nuevos tipos de evento
INSERT INTO public.tipos_evento (nombre, descripcion) VALUES
    ('Cumpleaños Infantil', 'Festejo de cumpleaños con juegos, música y área de diversión para niños.'),
    ('Día del Niño',        'Evento especial para celebrar el Día del Niño con actividades y sorpresas.'),
    ('Posada Navideña',     'Piñatas, villancicos y diversión navideña para grupos infantiles.'),
    ('Convivio Escolar',    'Salida o convivio para grupos escolares con actividades guiadas y supervisadas.'),
    ('Graduación Infantil', 'Festejo de fin de ciclo escolar para preescolar y primaria.'),
    ('Baby Shower',         'Celebración previa a la llegada del bebé, con espacio para toda la familia.')
ON CONFLICT (nombre) DO NOTHING;

-- 3. Nuevos paquetes: tres niveles, replicados para cada sucursal activa
INSERT INTO public.paquetes
    (sucursal_id, nombre, descripcion, duracion_minutos, personas_incluidas, precio_base, precio_persona_extra)
SELECT s.id, pk.nombre, pk.descripcion, pk.duracion_minutos, pk.personas_incluidas,
       pk.precio_base, pk.precio_persona_extra
FROM public.sucursales s
CROSS JOIN (VALUES
    ('Paquete Explorador', 'Acceso a las áreas de juego, pulsera de acceso y mesa decorada básica.', 90, 15, 2800.00, 120.00),
    ('Paquete Aventura',   'Acceso a juegos, alberca de pelotas y trampolines, decoración temática y anfitrión asignado.', 120, 20, 4200.00, 150.00),
    ('Paquete Fiesta VIP', 'Salón privado, decoración premium, piñata incluida, mesero dedicado y acceso ilimitado a todas las áreas.', 150, 25, 6500.00, 180.00)
) AS pk(nombre, descripcion, duracion_minutos, personas_incluidas, precio_base, precio_persona_extra)
WHERE s.activo = true
  AND NOT EXISTS (
    SELECT 1 FROM public.paquetes p
    WHERE p.sucursal_id = s.id AND p.nombre = pk.nombre AND p.activo = true
  );

-- 4. Relacionar cada paquete nuevo con todos los tipos de evento nuevos
INSERT INTO public.paquete_tipos_evento (paquete_id, tipo_evento_id)
SELECT p.id, t.id
FROM public.paquetes p
JOIN public.sucursales s ON s.id = p.sucursal_id AND s.activo = true
CROSS JOIN public.tipos_evento t
WHERE p.nombre IN ('Paquete Explorador', 'Paquete Aventura', 'Paquete Fiesta VIP')
  AND p.activo = true
  AND t.nombre IN ('Cumpleaños Infantil', 'Día del Niño', 'Posada Navideña',
                    'Convivio Escolar', 'Graduación Infantil', 'Baby Shower')
ON CONFLICT DO NOTHING;
