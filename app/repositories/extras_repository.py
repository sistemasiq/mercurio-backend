from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

_SELECT = """
    SELECT id, sucursal_id, nombre, descripcion, precio, unidad,
           activo, creado, creado_por, modificado, modificado_por
    FROM extras
"""


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[dict[str, Any]]:
    if sucursal_id:
        rows = await conn.fetch(
            _SELECT + " WHERE activo = TRUE AND (sucursal_id = $1 OR sucursal_id IS NULL)",
            sucursal_id,
        )
    else:
        rows = await conn.fetch(_SELECT + " WHERE activo = TRUE")
    return [dict(r) for r in rows]


async def obtener(conn: asyncpg.Connection, extra_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(_SELECT + " WHERE id = $1", extra_id)
    return dict(row) if row else None


async def crear(
    conn: asyncpg.Connection,
    sucursal_id: UUID | None,
    nombre: str,
    descripcion: str | None,
    precio: Decimal,
    unidad: str,
) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        INSERT INTO extras (sucursal_id, nombre, descripcion, precio, unidad)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, sucursal_id, nombre, descripcion, precio, unidad,
                  activo, creado, creado_por, modificado, modificado_por
        """,
        sucursal_id,
        nombre,
        descripcion,
        precio,
        unidad,
    )
    return dict(row)


async def actualizar(
    conn: asyncpg.Connection, extra_id: UUID, updates: dict[str, Any]
) -> dict[str, Any] | None:
    if not updates:
        return await obtener(conn, extra_id)
    set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
    set_parts.append("modificado = NOW()")
    sql = (
        f"UPDATE extras SET {', '.join(set_parts)} WHERE id = $1 AND activo = TRUE "
        "RETURNING id, sucursal_id, nombre, descripcion, precio, unidad, "
        "activo, creado, creado_por, modificado, modificado_por"
    )
    row = await conn.fetchrow(sql, extra_id, *updates.values())
    return dict(row) if row else None


async def eliminar(conn: asyncpg.Connection, extra_id: UUID) -> bool:
    result = await conn.execute(
        "UPDATE extras SET activo = FALSE, modificado = NOW() WHERE id = $1 AND activo = TRUE",
        extra_id,
    )
    return bool(result == "UPDATE 1")
