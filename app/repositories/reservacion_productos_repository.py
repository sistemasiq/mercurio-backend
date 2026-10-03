from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

_SELECT = """
    SELECT id, reservacion_id, producto_id, cantidad, precio_unitario, subtotal, notas,
           creado, creado_por
    FROM reservacion_productos
"""


async def listar_por_reservacion(
    conn: asyncpg.Connection, reservacion_id: UUID
) -> list[dict[str, Any]]:
    rows = await conn.fetch(_SELECT + " WHERE reservacion_id = $1", reservacion_id)
    return [dict(r) for r in rows]


async def obtener(conn: asyncpg.Connection, reservacion_producto_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(_SELECT + " WHERE id = $1", reservacion_producto_id)
    return dict(row) if row else None


async def listar_con_nombre_por_reservacion(
    conn: asyncpg.Connection, reservacion_id: UUID
) -> list[dict[str, Any]]:
    """Igual que listar_por_reservacion, pero con el nombre del producto vía
    join — para armar la comanda de cocina."""
    sql = """
        SELECT rp.producto_id, p.nombre, rp.cantidad, rp.precio_unitario, rp.notas
        FROM public.reservacion_productos rp
        INNER JOIN public.productos p ON rp.producto_id = p.id
        WHERE rp.reservacion_id = $1
    """
    rows = await conn.fetch(sql, reservacion_id)
    return [dict(r) for r in rows]


async def crear(
    conn: asyncpg.Connection,
    reservacion_id: UUID,
    producto_id: UUID,
    cantidad: int,
    precio_unitario: Decimal,
    notas: str | None,
    creado_por: UUID | None = None,
) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        INSERT INTO reservacion_productos
            (reservacion_id, producto_id, cantidad, precio_unitario, notas, creado_por)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, reservacion_id, producto_id, cantidad, precio_unitario, subtotal, notas,
                  creado, creado_por
        """,
        reservacion_id,
        producto_id,
        cantidad,
        precio_unitario,
        notas,
        creado_por,
    )
    return dict(row)


async def actualizar(
    conn: asyncpg.Connection, reservacion_producto_id: UUID, updates: dict[str, Any]
) -> dict[str, Any] | None:
    if not updates:
        return await obtener(conn, reservacion_producto_id)
    set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
    sql = (
        f"UPDATE reservacion_productos SET {', '.join(set_parts)} WHERE id = $1 "
        "RETURNING id, reservacion_id, producto_id, cantidad, precio_unitario, subtotal, notas, "
        "creado, creado_por"
    )
    row = await conn.fetchrow(sql, reservacion_producto_id, *updates.values())
    return dict(row) if row else None


async def eliminar(conn: asyncpg.Connection, reservacion_producto_id: UUID) -> bool:
    result = await conn.execute(
        "DELETE FROM reservacion_productos WHERE id = $1", reservacion_producto_id
    )
    return bool(result == "DELETE 1")
