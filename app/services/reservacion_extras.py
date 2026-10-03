from uuid import UUID

import asyncpg
from fastapi import HTTPException, status

from app.core.scope import sucursal_scope
from app.exceptions import NoEncontrado
from app.repositories import reservacion_extras_repository, reservaciones_repository
from app.schemas.auth import TokenData
from app.schemas.reservacion_extras import (
    ReservacionExtrasCreate,
    ReservacionExtrasOut,
    ReservacionExtrasUpdate,
)


async def listar_por_reservacion(
    conn: asyncpg.Connection, reservacion_id: UUID, current_user: TokenData
) -> list[ReservacionExtrasOut]:
    reservacion = await reservaciones_repository.obtener(conn, reservacion_id)
    if not reservacion:
        raise NoEncontrado("Reservación")

    scope = sucursal_scope(current_user)
    if scope is not None and str(reservacion["sucursal_id"]) != scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede consultar extras de reservaciones de otra sucursal.",
        )

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
