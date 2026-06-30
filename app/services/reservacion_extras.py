from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado
from app.repositories import reservacion_extras as repo
from app.schemas.reservacion_extras import (
    ReservacionExtrasCreate,
    ReservacionExtrasOut,
    ReservacionExtrasUpdate,
)


async def listar_por_reservacion(
    conn: asyncpg.Connection, reservacion_id: UUID
) -> list[ReservacionExtrasOut]:
    rows = await repo.listar_por_reservacion(conn, reservacion_id)
    return [ReservacionExtrasOut.model_validate(dict(r)) for r in rows]


async def obtener(conn: asyncpg.Connection, reservacion_extra_id: UUID) -> ReservacionExtrasOut:
    row = await repo.obtener_por_id(conn, reservacion_extra_id)
    if not row:
        raise NoEncontrado("Extra de reservación")
    return ReservacionExtrasOut.model_validate(dict(row))


async def crear(
    conn: asyncpg.Connection,
    body: ReservacionExtrasCreate,
    actor_id: UUID | None = None,
) -> ReservacionExtrasOut:
    try:
        row = await repo.crear(
            conn,
            reservacion_id=body.reservacion_id,
            extra_id=body.extra_id,
            cantidad=body.cantidad,
            precio_unitario=body.precio_unitario,
            creado_por=actor_id,
        )
    except asyncpg.ForeignKeyViolationError:
        raise NoEncontrado("Reservación o extra") from None
    return ReservacionExtrasOut.model_validate(dict(row))


async def actualizar(
    conn: asyncpg.Connection,
    reservacion_extra_id: UUID,
    body: ReservacionExtrasUpdate,
) -> ReservacionExtrasOut:
    actual = await obtener(conn, reservacion_extra_id)
    cambios = body.model_dump(exclude_unset=True)
    if not cambios:
        return actual
    row = await repo.actualizar(conn, reservacion_extra_id, cambios)
    assert row is not None  # garantizado por obtener() previo
    return ReservacionExtrasOut.model_validate(dict(row))


async def eliminar(conn: asyncpg.Connection, reservacion_extra_id: UUID) -> None:
    resultado = await repo.eliminar(conn, reservacion_extra_id)
    if resultado.endswith("0"):
        raise NoEncontrado("Extra de reservación")
