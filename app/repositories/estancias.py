import asyncpg
from uuid import UUID

async def get_activos_by_sucursal_id(conn: asyncpg.Connection,sucursal_id: UUID):
    rows = await conn.fetch("""
       SELECT
           r.id AS registro_id,
           dr.id AS detalle_id,

           n.nombre_completo AS nino,
           n.notas,
           n.edad,

           t.nombre_completo AS tutor,
           t.telefono,

           dr.parentesco,

           p.pulsera_rfid AS pulsera,

           (dr.cantidad * 60) AS minutos_pagados,

           FLOOR(
               EXTRACT(EPOCH FROM (NOW() - dr.entrada)) / 60
           ) AS minutos_transcurridos


       FROM detalles_registro dr

       JOIN registros r
           ON r.id = dr.registros_id

       JOIN ninos n
           ON n.id = dr.ninos_id


       JOIN tutores t
           ON t.id = r.tutores_id


       JOIN pulseras p
           ON p.id = dr.pulseras_id


       WHERE dr.sucursal_id = $1
       AND r.estado = 'A'
       AND dr.salida IS NULL


       ORDER BY dr.entrada;
   """, sucursal_id)


    return [dict(r) for r in rows]