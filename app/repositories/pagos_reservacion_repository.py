from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

_SELECT = """
    SELECT id, reservacion_id, metodo_pago_id, monto, fecha_pago, notas, creado_por
    FROM pagos_reservacion
"""


async def listar_todos(
    conn: asyncpg.Connection, sucursal_id: str | None = None
) -> list[dict[str, Any]]:
    if sucursal_id is not None:
        rows = await conn.fetch(
            """
            SELECT pr.id, pr.reservacion_id, pr.metodo_pago_id, pr.monto, pr.fecha_pago,
                   pr.notas, pr.creado_por
            FROM pagos_reservacion pr
            JOIN reservaciones r ON r.id = pr.reservacion_id
            WHERE r.sucursal_id = $1
            ORDER BY pr.fecha_pago DESC
            """,
            sucursal_id,
        )
    else:
        rows = await conn.fetch(_SELECT + " ORDER BY fecha_pago DESC")
    return [dict(r) for r in rows]


async def listar_por_reservacion(
    conn: asyncpg.Connection, reservacion_id: UUID
) -> list[dict[str, Any]]:
    rows = await conn.fetch(_SELECT + " WHERE reservacion_id = $1", reservacion_id)
    return [dict(r) for r in rows]


async def obtener(conn: asyncpg.Connection, pago_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(_SELECT + " WHERE id = $1", pago_id)
    return dict(row) if row else None


async def crear(
    conn: asyncpg.Connection,
    reservacion_id: UUID,
    metodo_pago_id: UUID,
    monto: Decimal,
    fecha_pago: datetime,
    notas: str | None,
    creado_por: UUID | None = None,
) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        INSERT INTO pagos_reservacion (reservacion_id, metodo_pago_id, monto, fecha_pago, notas, creado_por)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, reservacion_id, metodo_pago_id, monto, fecha_pago, notas, creado_por
        """,
        reservacion_id,
        metodo_pago_id,
        monto,
        fecha_pago,
        notas,
        creado_por,
    )
    return dict(row)


async def actualizar(
    conn: asyncpg.Connection, pago_id: UUID, updates: dict[str, Any]
) -> dict[str, Any] | None:
    if not updates:
        return await obtener(conn, pago_id)
    set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
    sql = (
        f"UPDATE pagos_reservacion SET {', '.join(set_parts)} WHERE id = $1 "
        "RETURNING id, reservacion_id, metodo_pago_id, monto, fecha_pago, notas, creado_por"
    )
    row = await conn.fetchrow(sql, pago_id, *updates.values())
    return dict(row) if row else None


async def eliminar(conn: asyncpg.Connection, pago_id: UUID) -> bool:
    result = await conn.execute("DELETE FROM pagos_reservacion WHERE id = $1", pago_id)
    return bool(result == "DELETE 1")
