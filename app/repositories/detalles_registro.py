import asyncpg
from uuid import UUID
from datetime import datetime, timezone


async def count_detalles_registro_abiertos(conn,registro_id:UUID)->int:
    return await conn.fetchval("""
               SELECT COUNT(*)
               FROM detalles_registro
               WHERE registros_id = $1
               AND salida IS NULL
               AND activo = TRUE
           """,
               registro_id
           )

async def get_detalle_registro_by_id(conn: asyncpg.Connection,detalle_registro: UUID):
    return await conn.fetchrow("""
        SELECT *
        FROM detalles_registro
        WHERE id = $1
        AND activo = TRUE
    """,detalle_registro)

async def insert_detalle_registro(
    conn,
    sucursal_id:UUID,
    registro_id:UUID,
    nino_id:UUID,
    pulsera_id:UUID,
    producto_id:UUID,
    cantidad:int,
    precio:float,
    parentesco:str,
    entrada,
    salida_esperada,
    usuario_id:UUID
):
    await conn.execute("""
        INSERT INTO detalles_registro (
            sucursal_id,
            registros_id,
            ninos_id,
            pulseras_id,
            productos_id,
            cantidad,
            precio,
            parentesco,
            entrada,
            salida_esperada,
            creado_por
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        """,
                   sucursal_id,
                   registro_id,
                   nino_id,
                   pulsera_id,
                   producto_id,
                   cantidad,
                   precio,
                   parentesco,
                   entrada,
                   salida_esperada,
                   usuario_id
               )

async def put_hora_salida_by_id(conn: asyncpg.Connection, usuario_id:UUID,detalle_registro:UUID):
    now = datetime.now(timezone.utc)
    await conn.execute("""
               UPDATE detalles_registro
               SET salida = $1,
                   modificado = NOW(),
                   modificado_por = $2
               WHERE id = $3
           """,
               now,
               usuario_id,
               detalle_registro
           )