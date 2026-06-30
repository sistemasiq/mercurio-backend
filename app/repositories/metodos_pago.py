from typing import Any
from uuid import UUID

import asyncpg

from app.repositories._sql import build_update


async def listar(conn: asyncpg.Connection) -> list[asyncpg.Record]:
    return await conn.fetch("SELECT * FROM public.metodos_pago WHERE activo = TRUE ORDER BY creado")


async def obtener_por_id(conn: asyncpg.Connection, metodo_pago_id: UUID) -> asyncpg.Record | None:
    return await conn.fetchrow("SELECT * FROM public.metodos_pago WHERE id = $1", metodo_pago_id)


async def crear(
    conn: asyncpg.Connection,
    *,
    nombre: str,
    descripcion: str | None,
    creado_por: UUID | None,
) -> asyncpg.Record:
    return await conn.fetchrow(
        """
        INSERT INTO public.metodos_pago (nombre, descripcion, creado_por)
        VALUES ($1, $2, $3)
        RETURNING *
        """,
        nombre,
        descripcion,
        creado_por,
    )


async def actualizar(
    conn: asyncpg.Connection,
    metodo_pago_id: UUID,
    cambios: dict[str, Any],
    *,
    modificado_por: UUID | None,
) -> asyncpg.Record | None:
    query, args = build_update(
        "metodos_pago", cambios, id_val=metodo_pago_id, modificado_por=modificado_por
    )
    return await conn.fetchrow(query, *args)


async def desactivar(
    conn: asyncpg.Connection, metodo_pago_id: UUID, *, modificado_por: UUID | None
) -> None:
    await conn.execute(
        """
        UPDATE public.metodos_pago
        SET activo = FALSE, modificado = now(), modificado_por = $2
        WHERE id = $1
        """,
        metodo_pago_id,
        modificado_por,
    )
