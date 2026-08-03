from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import asyncpg


async def count_detalles_registro_abiertos(conn: asyncpg.Connection, registro_id: UUID) -> int:
    result = await conn.fetchval(
        """
               SELECT COUNT(*)
               FROM detalles_registro
               WHERE registros_id = $1
               AND salida IS NULL
               AND activo = TRUE
           """,
        registro_id,
    )
    return int(result)


async def get_detalle_registro_by_id(
    conn: asyncpg.Connection, detalle_registro: UUID
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT *
        FROM detalles_registro
        WHERE id = $1
        AND activo = TRUE
    """,
        detalle_registro,
    )


async def insert_detalle_registro(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    registro_id: UUID,
    nino_id: UUID,
    pulsera_id: UUID,
    parentesco: str,
    entrada: datetime,
    salida_esperada: datetime,
    usuario_id: UUID,
    cantidad: int = 0,
    precio: Decimal = Decimal("0.0"),
    producto_id: UUID | None = None,
) -> None:
    await conn.execute(
        """
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
        usuario_id,
    )


async def put_hora_salida_by_id(
    conn: asyncpg.Connection, usuario_id: UUID, detalle_registro: UUID
) -> None:
    now = datetime.now(UTC)
    await conn.execute(
        """
               UPDATE detalles_registro
               SET salida = $1,
                   modificado = NOW(),
                   modificado_por = $2
               WHERE id = $3
           """,
        now,
        usuario_id,
        detalle_registro,
    )
