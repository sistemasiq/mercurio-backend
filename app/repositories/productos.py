import asyncpg
from uuid import UUID

async def get_precio_individual_by_id(conn: asyncpg.Connection, prducto_id: UUID):
    return await conn.fetchval(
            "SELECT precio_unitario FROM productos WHERE id = $1",
                prducto_id
    )

async def get_productos_estancia_by_sucursal_id(conn: asyncpg.Connection, sucursal_id: UUID):
    rows = await conn.fetch("""
       SELECT
           id,
           nombre,
           precio_unitario,
           descripcion
       FROM productos
       WHERE sucursal_id = $1
         AND activo = TRUE
         AND tipo = 'E'
       ORDER BY precio_unitario
   """, sucursal_id)


    return [dict(r) for r in rows]