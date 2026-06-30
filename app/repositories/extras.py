from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

from app.repositories._sql import build_update


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[asyncpg.Record]:
    """Extras activos. Si se da sucursal_id, incluye los de esa sucursal y los globales."""
    if sucursal_id is not None:
        return await conn.fetch(
            """
            SELECT * FROM public.extras
            WHERE activo = TRUE AND (sucursal_id = $1 OR sucursal_id IS NULL)
            ORDER BY creado
            """,
            sucursal_id,
        )
    return await conn.fetch("SELECT * FROM public.extras WHERE activo = TRUE ORDER BY creado")


async def obtener_por_id(conn: asyncpg.Connection, extra_id: UUID) -> asyncpg.Record | None:
    return await conn.fetchrow("SELECT * FROM public.extras WHERE id = $1", extra_id)


async def crear(
    conn: asyncpg.Connection,
    *,
    sucursal_id: UUID | None,
    nombre: str,
    descripcion: str | None,
    precio: Decimal,
    unidad: str,
    creado_por: UUID | None,
) -> asyncpg.Record:
    return await conn.fetchrow(
        """
        INSERT INTO public.extras
            (sucursal_id, nombre, descripcion, precio, unidad, creado_por)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """,
        sucursal_id,
        nombre,
        descripcion,
        precio,
        unidad,
        creado_por,
    )


async def actualizar(
    conn: asyncpg.Connection,
    extra_id: UUID,
    cambios: dict[str, Any],
    *,
    modificado_por: UUID | None,
) -> asyncpg.Record | None:
    query, args = build_update("extras", cambios, id_val=extra_id, modificado_por=modificado_por)
    return await conn.fetchrow(query, *args)


async def desactivar(
    conn: asyncpg.Connection, extra_id: UUID, *, modificado_por: UUID | None
) -> None:
    await conn.execute(
        """
        UPDATE public.extras
        SET activo = FALSE, modificado = now(), modificado_por = $2
        WHERE id = $1
        """,
        extra_id,
        modificado_por,
    )
