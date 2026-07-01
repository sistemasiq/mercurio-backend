from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

_SELECT = """
    SELECT id, sucursal_id, nombre, descripcion, duracion_minutos, personas_incluidas,
           precio_base, precio_persona_extra, activo, creado, creado_por,
           modificado, modificado_por
    FROM paquetes
"""


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[dict[str, Any]]:
    if sucursal_id:
        rows = await conn.fetch(_SELECT + " WHERE activo = TRUE AND sucursal_id = $1", sucursal_id)
    else:
        rows = await conn.fetch(_SELECT + " WHERE activo = TRUE")
    return [dict(r) for r in rows]


async def obtener(conn: asyncpg.Connection, paquete_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(_SELECT + " WHERE id = $1", paquete_id)
    return dict(row) if row else None


async def crear(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    nombre: str,
    descripcion: str | None,
    duracion_minutos: int,
    personas_incluidas: int,
    precio_base: Decimal,
    precio_persona_extra: Decimal,
) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        INSERT INTO paquetes
            (sucursal_id, nombre, descripcion, duracion_minutos, personas_incluidas,
             precio_base, precio_persona_extra)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, sucursal_id, nombre, descripcion, duracion_minutos, personas_incluidas,
                  precio_base, precio_persona_extra, activo, creado, creado_por,
                  modificado, modificado_por
        """,
        sucursal_id,
        nombre,
        descripcion,
        duracion_minutos,
        personas_incluidas,
        precio_base,
        precio_persona_extra,
    )
    return dict(row)


async def actualizar(
    conn: asyncpg.Connection, paquete_id: UUID, updates: dict[str, Any]
) -> dict[str, Any] | None:
    if not updates:
        return await obtener(conn, paquete_id)
    set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
    set_parts.append("modificado = NOW()")
    sql = (
        f"UPDATE paquetes SET {', '.join(set_parts)} WHERE id = $1 AND activo = TRUE "
        "RETURNING id, sucursal_id, nombre, descripcion, duracion_minutos, personas_incluidas, "
        "precio_base, precio_persona_extra, activo, creado, creado_por, modificado, modificado_por"
    )
    row = await conn.fetchrow(sql, paquete_id, *updates.values())
    return dict(row) if row else None


async def eliminar(conn: asyncpg.Connection, paquete_id: UUID) -> bool:
    result = await conn.execute(
        "UPDATE paquetes SET activo = FALSE, modificado = NOW() WHERE id = $1 AND activo = TRUE",
        paquete_id,
    )
    return bool(result == "UPDATE 1")
