from typing import Any
from uuid import UUID

import asyncpg


async def get_pulseras_by_sucursal(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
       SELECT
           p.id,
           p.pulsera_rfid
       FROM pulseras p
       WHERE p.sucursal_id = $1
         AND p.activo = TRUE
         AND NOT EXISTS (
               SELECT 1
               FROM detalles_registro dr
               JOIN registros r
                   ON r.id = dr.registros_id
               WHERE dr.pulseras_id = p.id
                 AND r.estado = 'A'
                 AND dr.salida IS NULL
         )
       ORDER BY p.pulsera_rfid
   """,
        sucursal_id,
    )

    return [dict(r) for r in rows]
