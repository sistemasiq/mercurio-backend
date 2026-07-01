from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado
from app.repositories import reservacion_extras_repository
from app.schemas.reservacion_extras import (
    ReservacionExtrasCreate,
    ReservacionExtrasOut,
    ReservacionExtrasUpdate,
)


async def listar_por_reservacion(
    conn: asyncpg.Connection, reservacion_id: UUID
) -> list[ReservacionExtrasOut]:
    rows = await reservacion_extras_repository.listar_por_reservacion(conn, reservacion_id)
    return [ReservacionExtrasOut.model_validate(r) for r in rows]


async def obtener(conn: asyncpg.Connection, reservacion_extra_id: UUID) -> ReservacionExtrasOut:
    row = await reservacion_extras_repository.obtener(conn, reservacion_extra_id)
    if not row:
        raise NoEncontrado("Extra de reservación")
    return ReservacionExtrasOut.model_validate(row)


async def crear(conn: asyncpg.Connection, body: ReservacionExtrasCreate) -> ReservacionExtrasOut:
    row = await reservacion_extras_repository.crear(
        conn,
        reservacion_id=body.reservacion_id,
        extra_id=body.extra_id,
        cantidad=body.cantidad,
        precio_unitario=body.precio_unitario,
    )
    return ReservacionExtrasOut.model_validate(row)


async def actualizar(
    conn: asyncpg.Connection, reservacion_extra_id: UUID, body: ReservacionExtrasUpdate
) -> ReservacionExtrasOut:
    await obtener(conn, reservacion_extra_id)
    updates = body.model_dump(exclude_unset=True)
    row = await reservacion_extras_repository.actualizar(conn, reservacion_extra_id, updates)
    if not row:
        raise NoEncontrado("Extra de reservación")
    return ReservacionExtrasOut.model_validate(row)


async def eliminar(conn: asyncpg.Connection, reservacion_extra_id: UUID) -> None:
    await obtener(conn, reservacion_extra_id)
    await reservacion_extras_repository.eliminar(conn, reservacion_extra_id)
