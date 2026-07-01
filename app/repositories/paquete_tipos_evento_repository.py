from typing import Any
from uuid import UUID

import asyncpg


async def listar_por_paquete(conn: asyncpg.Connection, paquete_id: UUID) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        "SELECT paquete_id, tipo_evento_id FROM paquete_tipos_evento WHERE paquete_id = $1",
        paquete_id,
    )
    return [dict(r) for r in rows]


async def obtener(
    conn: asyncpg.Connection, paquete_id: UUID, tipo_evento_id: UUID
) -> dict[str, Any] | None:
    row = await conn.fetchrow(
        "SELECT paquete_id, tipo_evento_id FROM paquete_tipos_evento "
        "WHERE paquete_id = $1 AND tipo_evento_id = $2",
        paquete_id,
        tipo_evento_id,
    )
    return dict(row) if row else None


async def agregar(
    conn: asyncpg.Connection, paquete_id: UUID, tipo_evento_id: UUID
) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        INSERT INTO paquete_tipos_evento (paquete_id, tipo_evento_id)
        VALUES ($1, $2)
        RETURNING paquete_id, tipo_evento_id
        """,
        paquete_id,
        tipo_evento_id,
    )
    return dict(row)


async def eliminar(conn: asyncpg.Connection, paquete_id: UUID, tipo_evento_id: UUID) -> bool:
    result = await conn.execute(
        "DELETE FROM paquete_tipos_evento WHERE paquete_id = $1 AND tipo_evento_id = $2",
        paquete_id,
        tipo_evento_id,
    )
    return bool(result == "DELETE 1")
