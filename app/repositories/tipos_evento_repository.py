from typing import Any
from uuid import UUID

import asyncpg

_SELECT = """
    SELECT id, sucursal_id, nombre, descripcion, activo, creado, creado_por, modificado,
           modificado_por
    FROM tipos_evento
"""

# Igual que _SELECT pero agregando cuántos paquetes activos tiene asociados
# cada tipo de evento (vía paquete_tipos_evento), para la columna
# "paquetes_count" del listado.
_SELECT_CON_PAQUETES_COUNT = """
    SELECT te.id, te.sucursal_id, te.nombre, te.descripcion, te.activo, te.creado,
           te.creado_por, te.modificado, te.modificado_por,
           COUNT(p.id) AS paquetes_count
    FROM tipos_evento te
    LEFT JOIN paquete_tipos_evento pte ON pte.tipo_evento_id = te.id
    LEFT JOIN paquetes p ON p.id = pte.paquete_id AND p.activo = TRUE
"""

_GROUP_ORDER = " GROUP BY te.id ORDER BY te.nombre ASC"


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[dict[str, Any]]:
    if sucursal_id:
        rows = await conn.fetch(
            _SELECT_CON_PAQUETES_COUNT
            + " WHERE te.activo = TRUE AND (te.sucursal_id = $1 OR te.sucursal_id IS NULL)"
            + _GROUP_ORDER,
            sucursal_id,
        )
    else:
        rows = await conn.fetch(
            _SELECT_CON_PAQUETES_COUNT + " WHERE te.activo = TRUE" + _GROUP_ORDER
        )
    return [dict(r) for r in rows]


async def obtener(conn: asyncpg.Connection, tipo_evento_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(_SELECT + " WHERE id = $1", tipo_evento_id)
    return dict(row) if row else None


async def nombre_existe(conn: asyncpg.Connection, nombre: str, sucursal_id: UUID | None) -> bool:
    row = await conn.fetchrow(
        """
        SELECT id FROM tipos_evento
        WHERE nombre = $1 AND activo = TRUE
          AND (sucursal_id = $2 OR sucursal_id IS NULL OR $2 IS NULL)
        """,
        nombre,
        sucursal_id,
    )
    return row is not None


async def crear(
    conn: asyncpg.Connection, sucursal_id: UUID | None, nombre: str, descripcion: str | None
) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        INSERT INTO tipos_evento (sucursal_id, nombre, descripcion)
        VALUES ($1, $2, $3)
        RETURNING id, sucursal_id, nombre, descripcion, activo, creado, creado_por, modificado,
                  modificado_por
        """,
        sucursal_id,
        nombre,
        descripcion,
    )
    return dict(row)


async def actualizar(
    conn: asyncpg.Connection, tipo_evento_id: UUID, updates: dict[str, Any]
) -> dict[str, Any] | None:
    if not updates:
        return await obtener(conn, tipo_evento_id)
    set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
    set_parts.append("modificado = NOW()")
    sql = (
        f"UPDATE tipos_evento SET {', '.join(set_parts)} WHERE id = $1 AND activo = TRUE "
        "RETURNING id, sucursal_id, nombre, descripcion, activo, creado, creado_por, "
        "modificado, modificado_por"
    )
    row = await conn.fetchrow(sql, tipo_evento_id, *updates.values())
    return dict(row) if row else None


async def eliminar(conn: asyncpg.Connection, tipo_evento_id: UUID) -> bool:
    result = await conn.execute(
        "UPDATE tipos_evento SET activo = FALSE, modificado = NOW() "
        "WHERE id = $1 AND activo = TRUE",
        tipo_evento_id,
    )
    return bool(result == "UPDATE 1")
