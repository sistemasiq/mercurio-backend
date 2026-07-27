"""
app/repositories/presentacion_insumo_repository.py
Única capa que habla con la BD para presentaciones de compra de un insumo —
SQL crudo con asyncpg. Regla 11.1 y 11.4 SAD.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

_COLUMNS = """
    id, insumo_id, nombre, equivalencia_base,
    activo, creado, creado_por, modificado, modificado_por
"""


async def listar_por_insumo(conn: asyncpg.Connection, insumo_id: UUID) -> list[dict[str, Any]]:
    """Lista presentaciones (activas e inactivas) de un insumo, para la
    pantalla de administración."""
    rows = await conn.fetch(
        f"SELECT {_COLUMNS} FROM public.presentaciones_insumo "
        "WHERE insumo_id = $1 ORDER BY nombre ASC",
        insumo_id,
    )
    return [dict(r) for r in rows]


async def obtener(conn: asyncpg.Connection, presentacion_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(
        f"SELECT {_COLUMNS} FROM public.presentaciones_insumo WHERE id = $1", presentacion_id
    )
    return dict(row) if row else None


async def crear(
    conn: asyncpg.Connection,
    insumo_id: UUID,
    nombre: str,
    equivalencia_base: Decimal,
    creado_por: UUID,
) -> dict[str, Any]:
    row = await conn.fetchrow(
        f"""
        INSERT INTO public.presentaciones_insumo (insumo_id, nombre, equivalencia_base, creado_por)
        VALUES ($1, $2, $3, $4)
        RETURNING {_COLUMNS}
        """,
        insumo_id,
        nombre,
        equivalencia_base,
        creado_por,
    )
    return dict(row)


async def actualizar(
    conn: asyncpg.Connection, presentacion_id: UUID, updates: dict[str, Any]
) -> dict[str, Any] | None:
    if not updates:
        return await obtener(conn, presentacion_id)
    set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
    set_parts.append("modificado = NOW()")
    sql = (
        f"UPDATE public.presentaciones_insumo SET {', '.join(set_parts)} WHERE id = $1 "
        f"RETURNING {_COLUMNS}"
    )
    row = await conn.fetchrow(sql, presentacion_id, *updates.values())
    return dict(row) if row else None


async def eliminar(conn: asyncpg.Connection, presentacion_id: UUID) -> bool:
    result = await conn.execute(
        "UPDATE public.presentaciones_insumo SET activo = FALSE, modificado = NOW() "
        "WHERE id = $1 AND activo = TRUE",
        presentacion_id,
    )
    return bool(result == "UPDATE 1")
