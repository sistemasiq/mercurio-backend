from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

from app.repositories._sql import build_update


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[asyncpg.Record]:
    if sucursal_id is not None:
        return await conn.fetch(
            """
            SELECT * FROM public.paquetes
            WHERE activo = TRUE AND sucursal_id = $1
            ORDER BY creado
            """,
            sucursal_id,
        )
    return await conn.fetch("SELECT * FROM public.paquetes WHERE activo = TRUE ORDER BY creado")


async def obtener_por_id(conn: asyncpg.Connection, paquete_id: UUID) -> asyncpg.Record | None:
    return await conn.fetchrow("SELECT * FROM public.paquetes WHERE id = $1", paquete_id)


async def crear(
    conn: asyncpg.Connection,
    *,
    sucursal_id: UUID,
    nombre: str,
    descripcion: str | None,
    duracion_minutos: int,
    personas_incluidas: int,
    precio_base: Decimal,
    precio_persona_extra: Decimal,
    creado_por: UUID | None,
) -> asyncpg.Record:
    return await conn.fetchrow(
        """
        INSERT INTO public.paquetes
            (sucursal_id, nombre, descripcion, duracion_minutos,
             personas_incluidas, precio_base, precio_persona_extra, creado_por)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING *
        """,
        sucursal_id,
        nombre,
        descripcion,
        duracion_minutos,
        personas_incluidas,
        precio_base,
        precio_persona_extra,
        creado_por,
    )


async def actualizar(
    conn: asyncpg.Connection,
    paquete_id: UUID,
    cambios: dict[str, Any],
    *,
    modificado_por: UUID | None,
) -> asyncpg.Record | None:
    query, args = build_update(
        "paquetes", cambios, id_val=paquete_id, modificado_por=modificado_por
    )
    return await conn.fetchrow(query, *args)


async def desactivar(
    conn: asyncpg.Connection, paquete_id: UUID, *, modificado_por: UUID | None
) -> None:
    await conn.execute(
        """
        UPDATE public.paquetes
        SET activo = FALSE, modificado = now(), modificado_por = $2
        WHERE id = $1
        """,
        paquete_id,
        modificado_por,
    )
