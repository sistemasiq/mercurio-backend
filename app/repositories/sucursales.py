from uuid import UUID

import asyncpg


async def exists_sucursal(conn: asyncpg.Connection, sucursal_id: UUID) -> bool:
    result = await conn.fetchval(
        """
       SELECT EXISTS(
           SELECT 1
           FROM sucursales
           WHERE id = $1
       )
       """,
        sucursal_id,
    )
    return bool(result)
