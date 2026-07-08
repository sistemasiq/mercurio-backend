from typing import Any
from uuid import UUID

import asyncpg


async def get_pulseras_disponibles_por_sucursal(
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
            WHERE dr.pulseras_id = p.id
        )
        AND NOT EXISTS (
            SELECT 1
            FROM registros r
            WHERE r.pulseras_tutor_id = p.id
        )
        ORDER BY p.pulsera_rfid
        """,
        sucursal_id,
    )

    return [dict(r) for r in rows]
