-- =============================================================================
-- 039_paquetes_precio_hora_pulsera.sql
-- La pulsera pasa a cobrarse POR HORA de evento, no una sola vez.
--
--   antes: precio_base + precio_pulsera x invitados
--   ahora: precio_base + precio_hora_pulsera x invitados x horas del evento
--
-- Las horas vuelven así al cálculo del precio, del que salieron en la
-- migración 034 (que eliminó precio_hora del paquete). La diferencia es dónde
-- se aplican: aquélla cobraba una tarifa por hora del salón, independiente de
-- cuánta gente asistiera; ésta cobra la pulsera de cada invitado por cada hora
-- que dura el evento. reservaciones.horas_reservadas —que la 034 conservó a
-- propósito— es justo el dato que hacía falta.
--
-- Los valores existentes se ponen en CERO en lugar de conservarse: se
-- capturaron como precio por evento y reinterpretarlos por hora multiplicaría
-- el cobro por la duración sin que nadie lo decidiera (un paquete de $180 con
-- un evento de 3 horas pasaría a cobrar $540 por invitado, en silencio). En
-- cero, ningún paquete cobra pulsera hasta que alguien defina conscientemente
-- la tarifa por hora, y mientras tanto sólo se cobra el precio base.
-- =============================================================================

ALTER TABLE public.paquetes
    RENAME COLUMN precio_pulsera TO precio_hora_pulsera;

UPDATE public.paquetes
   SET precio_hora_pulsera = 0
 WHERE precio_hora_pulsera <> 0;
