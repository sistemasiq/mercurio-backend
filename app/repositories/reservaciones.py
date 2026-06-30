from typing import Any
from uuid import UUID

import asyncpg

from app.repositories._sql import build_update


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[asyncpg.Record]:
    if sucursal_id is not None:
        return await conn.fetch(
            """
            SELECT * FROM public.reservaciones
            WHERE activo = TRUE AND sucursal_id = $1
            ORDER BY fecha_evento DESC, hora_inicio
            """,
            sucursal_id,
        )
    return await conn.fetch(
        """
        SELECT * FROM public.reservaciones
        WHERE activo = TRUE
        ORDER BY fecha_evento DESC, hora_inicio
        """
    )


async def obtener_por_id(conn: asyncpg.Connection, reservacion_id: UUID) -> asyncpg.Record | None:
    return await conn.fetchrow("SELECT * FROM public.reservaciones WHERE id = $1", reservacion_id)


async def crear(
    conn: asyncpg.Connection, datos: dict[str, Any], *, creado_por: UUID | None
) -> asyncpg.Record:
    """Inserta una reservación. ``datos`` son los campos del schema (sin saldo_pendiente)."""
    columnas = [*datos.keys(), "creado_por"]
    valores = [*datos.values(), creado_por]
    placeholders = ", ".join(f"${i}" for i in range(1, len(valores) + 1))
    query = (
        f"INSERT INTO public.reservaciones ({', '.join(columnas)}) "
        f"VALUES ({placeholders}) RETURNING *"
    )
    return await conn.fetchrow(query, *valores)


async def actualizar(
    conn: asyncpg.Connection,
    reservacion_id: UUID,
    cambios: dict[str, Any],
    *,
    modificado_por: UUID | None,
) -> asyncpg.Record | None:
    query, args = build_update(
        "reservaciones", cambios, id_val=reservacion_id, modificado_por=modificado_por
    )
    return await conn.fetchrow(query, *args)


async def desactivar(
    conn: asyncpg.Connection, reservacion_id: UUID, *, modificado_por: UUID | None
) -> None:
    await conn.execute(
        """
        UPDATE public.reservaciones
        SET activo = FALSE, modificado = now(), modificado_por = $2
        WHERE id = $1
        """,
        reservacion_id,
        modificado_por,
    )
