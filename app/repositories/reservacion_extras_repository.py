from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

_SELECT = """
    SELECT id, reservacion_id, extra_id, cantidad, precio_unitario, subtotal, creado, creado_por
    FROM reservacion_extras
"""


async def listar_por_reservacion(
    conn: asyncpg.Connection, reservacion_id: UUID
) -> list[dict[str, Any]]:
    rows = await conn.fetch(_SELECT + " WHERE reservacion_id = $1", reservacion_id)
    return [dict(r) for r in rows]


async def obtener(conn: asyncpg.Connection, reservacion_extra_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(_SELECT + " WHERE id = $1", reservacion_extra_id)
    return dict(row) if row else None


async def crear(
    conn: asyncpg.Connection,
    reservacion_id: UUID,
    extra_id: UUID,
    cantidad: int,
    precio_unitario: Decimal,
) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        INSERT INTO reservacion_extras (reservacion_id, extra_id, cantidad, precio_unitario)
        VALUES ($1, $2, $3, $4)
        RETURNING id, reservacion_id, extra_id, cantidad, precio_unitario, subtotal,
                  creado, creado_por
        """,
        reservacion_id,
        extra_id,
        cantidad,
        precio_unitario,
    )
    return dict(row)


async def actualizar(
    conn: asyncpg.Connection, reservacion_extra_id: UUID, updates: dict[str, Any]
) -> dict[str, Any] | None:
    if not updates:
        return await obtener(conn, reservacion_extra_id)
    set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
    sql = (
        f"UPDATE reservacion_extras SET {', '.join(set_parts)} WHERE id = $1 "
        "RETURNING id, reservacion_id, extra_id, cantidad, precio_unitario, subtotal, "
        "creado, creado_por"
    )
    row = await conn.fetchrow(sql, reservacion_extra_id, *updates.values())
    return dict(row) if row else None


async def eliminar(conn: asyncpg.Connection, reservacion_extra_id: UUID) -> bool:
    result = await conn.execute(
        "DELETE FROM reservacion_extras WHERE id = $1", reservacion_extra_id
    )
    return bool(result == "DELETE 1")
