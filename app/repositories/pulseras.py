from typing import Any
from uuid import UUID

import asyncpg

_COLUMNS = """
    id, sucursal_id, pulsera_rfid, activo, creado, creado_por, modificado, modificado_por
"""


async def get_pulseras_disponibles_por_sucursal(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT
            p.id,
            p.pulsera_rfid
        FROM pulseras p
        WHERE p.sucursal_id = $1
        AND p.activo = TRUE
        AND NOT EXISTS (
            SELECT 1
            FROM detalles_registro dr
            WHERE dr.pulseras_id = p.id
        )
        AND NOT EXISTS (
            SELECT 1
            FROM registros r
            WHERE r.pulseras_tutor_id = p.id
        )
        ORDER BY p.pulsera_rfid
        """,
        sucursal_id,
    )

    return [dict(r) for r in rows]


async def listar_todas(conn: asyncpg.Connection, sucursal_id: UUID) -> list[dict[str, Any]]:
    """Lista todas las pulseras de una sucursal (activas e inactivas), para administración."""
    rows = await conn.fetch(
        f"SELECT {_COLUMNS} FROM public.pulseras WHERE sucursal_id = $1 ORDER BY pulsera_rfid",
        sucursal_id,
    )
    return [dict(r) for r in rows]


async def obtener(conn: asyncpg.Connection, pulsera_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(f"SELECT {_COLUMNS} FROM public.pulseras WHERE id = $1", pulsera_id)
    return dict(row) if row else None


async def crear(
    conn: asyncpg.Connection, sucursal_id: UUID, pulsera_rfid: str, creado_por: UUID
) -> dict[str, Any]:
    row = await conn.fetchrow(
        f"""
        INSERT INTO public.pulseras (sucursal_id, pulsera_rfid, creado_por)
        VALUES ($1, $2, $3)
        RETURNING {_COLUMNS}
        """,
        sucursal_id,
        pulsera_rfid,
        creado_por,
    )
    return dict(row)


async def actualizar(
    conn: asyncpg.Connection, pulsera_id: UUID, updates: dict[str, Any]
) -> dict[str, Any] | None:
    if not updates:
        return await obtener(conn, pulsera_id)
    set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
    set_parts.append("modificado = NOW()")
    sql = (
        f"UPDATE public.pulseras SET {', '.join(set_parts)} WHERE id = $1 " f"RETURNING {_COLUMNS}"
    )
    row = await conn.fetchrow(sql, pulsera_id, *updates.values())
    return dict(row) if row else None


async def eliminar(conn: asyncpg.Connection, pulsera_id: UUID) -> bool:
    result = await conn.execute(
        "UPDATE public.pulseras SET activo = FALSE, modificado = NOW() "
        "WHERE id = $1 AND activo = TRUE",
        pulsera_id,
    )
    return bool(result == "UPDATE 1")
