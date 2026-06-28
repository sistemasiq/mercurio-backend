from uuid import UUID

async def exists_sucursal(conn, sucursal_id: UUID) -> bool:
   return await conn.fetchval(
       """
       SELECT EXISTS(
           SELECT 1
           FROM sucursales
           WHERE id = $1
       )
       """,
       sucursal_id
   )
