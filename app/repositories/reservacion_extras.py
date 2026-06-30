from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

from app.repositories._sql import build_update


async def listar_por_reservacion(
    conn: asyncpg.Connection, reservacion_id: UUID
) -> list[asyncpg.Record]:
    return await conn.fetch(
        "SELECT * FROM public.reservacion_extras WHERE reservacion_id = $1 ORDER BY creado",
        reservacion_id,
    )


async def obtener_por_id(
    conn: asyncpg.Connection, reservacion_extra_id: UUID
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        "SELECT * FROM public.reservacion_extras WHERE id = $1", reservacion_extra_id
    )


async def crear(
    conn: asyncpg.Connection,
    *,
    reservacion_id: UUID,
    extra_id: UUID,
    cantidad: int,
    precio_unitario: Decimal,
    creado_por: UUID | None,
) -> asyncpg.Record:
    return await conn.fetchrow(
        """
        INSERT INTO public.reservacion_extras
            (reservacion_id, extra_id, cantidad, precio_unitario, creado_por)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """,
        reservacion_id,
        extra_id,
        cantidad,
        precio_unitario,
        creado_por,
    )


async def actualizar(
    conn: asyncpg.Connection, reservacion_extra_id: UUID, cambios: dict[str, Any]
) -> asyncpg.Record | None:
    query, args = build_update(
        "reservacion_extras",
        cambios,
        id_val=reservacion_extra_id,
        touch_modificado=False,
    )
    return await conn.fetchrow(query, *args)


async def eliminar(conn: asyncpg.Connection, reservacion_extra_id: UUID) -> str:
    return await conn.execute(
        "DELETE FROM public.reservacion_extras WHERE id = $1", reservacion_extra_id
    )
