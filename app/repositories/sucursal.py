from typing import Any
from uuid import UUID

import asyncpg

from app.repositories._sql import build_update


async def listar(conn: asyncpg.Connection) -> list[asyncpg.Record]:
    return await conn.fetch("SELECT * FROM public.sucursales WHERE activo = TRUE ORDER BY creado")


async def obtener_por_id(conn: asyncpg.Connection, sucursal_id: UUID) -> asyncpg.Record | None:
    return await conn.fetchrow("SELECT * FROM public.sucursales WHERE id = $1", sucursal_id)


async def crear(
    conn: asyncpg.Connection,
    *,
    nombre: str,
    direccion: str | None,
    telefono: str | None,
    creado_por: UUID | None,
) -> asyncpg.Record:
    return await conn.fetchrow(
        """
        INSERT INTO public.sucursales (nombre, direccion, telefono, creado_por)
        VALUES ($1, $2, $3, $4)
        RETURNING *
        """,
        nombre,
        direccion,
        telefono,
        creado_por,
    )


async def actualizar(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    cambios: dict[str, Any],
    *,
    modificado_por: UUID | None,
) -> asyncpg.Record | None:
    query, args = build_update(
        "sucursales", cambios, id_val=sucursal_id, modificado_por=modificado_por
    )
    return await conn.fetchrow(query, *args)


async def desactivar(
    conn: asyncpg.Connection, sucursal_id: UUID, *, modificado_por: UUID | None
) -> None:
    await conn.execute(
        """
        UPDATE public.sucursales
        SET activo = FALSE, modificado = now(), modificado_por = $2
        WHERE id = $1
        """,
        sucursal_id,
        modificado_por,
    )
