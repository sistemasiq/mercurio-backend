from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

from app.repositories._sql import build_update


async def listar(conn: asyncpg.Connection) -> list[asyncpg.Record]:
    return await conn.fetch("SELECT * FROM public.pagos_reservacion ORDER BY fecha_pago DESC")


async def listar_por_reservacion(
    conn: asyncpg.Connection, reservacion_id: UUID
) -> list[asyncpg.Record]:
    return await conn.fetch(
        "SELECT * FROM public.pagos_reservacion WHERE reservacion_id = $1 ORDER BY fecha_pago DESC",
        reservacion_id,
    )


async def obtener_por_id(conn: asyncpg.Connection, pago_id: UUID) -> asyncpg.Record | None:
    return await conn.fetchrow("SELECT * FROM public.pagos_reservacion WHERE id = $1", pago_id)


async def crear(
    conn: asyncpg.Connection,
    *,
    reservacion_id: UUID,
    metodo_pago_id: UUID,
    monto: Decimal,
    notas: str | None,
    creado_por: UUID | None,
) -> asyncpg.Record:
    return await conn.fetchrow(
        """
        INSERT INTO public.pagos_reservacion
            (reservacion_id, metodo_pago_id, monto, notas, creado_por)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """,
        reservacion_id,
        metodo_pago_id,
        monto,
        notas,
        creado_por,
    )


async def actualizar(
    conn: asyncpg.Connection, pago_id: UUID, cambios: dict[str, Any]
) -> asyncpg.Record | None:
    query, args = build_update("pagos_reservacion", cambios, id_val=pago_id, touch_modificado=False)
    return await conn.fetchrow(query, *args)


async def eliminar(conn: asyncpg.Connection, pago_id: UUID) -> str:
    return await conn.execute("DELETE FROM public.pagos_reservacion WHERE id = $1", pago_id)
