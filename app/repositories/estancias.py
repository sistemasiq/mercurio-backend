from typing import Any
from uuid import UUID

import asyncpg


async def get_activos_by_sucursal_id(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT
            r.id AS "registroId",
            r.nombre_segundo_tutor AS "nombreSegundoTutor",
            r.pulseras_tutor_id AS "pulseraTutorId",
            pt.pulsera_rfid AS "pulseraTutorRfid",
            dr.id AS "detalleId",
            n.nombre_completo AS "nino",
            n.notas,
            n.edad,
            t.nombre_completo AS "tutor",
            t.telefono,
            dr.parentesco,
            p.pulsera_rfid AS "pulsera",
            (dr.cantidad * 60) AS "minutosPagados",
            FLOOR(
                EXTRACT(EPOCH FROM (NOW() - dr.entrada)) / 60
            ) AS "minutosTranscurridos"
        FROM detalles_registro dr
        JOIN registros r
            ON r.id = dr.registros_id
        JOIN ninos n
            ON n.id = dr.ninos_id
        JOIN tutores t
            ON t.id = r.tutores_id
        JOIN pulseras p
            ON p.id = dr.pulseras_id
        JOIN pulseras pt
            ON pt.id = r.pulseras_tutor_id
        WHERE dr.sucursal_id = $1
        AND r.estado = 'A'
        AND dr.salida IS NULL
        ORDER BY dr.entrada;
        """,
        sucursal_id,
    )

    return [dict(r) for r in rows]