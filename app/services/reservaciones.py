from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado
from app.repositories import reservaciones as repo
from app.schemas.reservaciones import (
    ReservacionesCrear,
    ReservacionesOut,
    ReservacionesUpdate,
)


async def listar(
    conn: asyncpg.Connection, sucursal_id: UUID | None = None
) -> list[ReservacionesOut]:
    rows = await repo.listar(conn, sucursal_id)
    return [ReservacionesOut.model_validate(dict(r)) for r in rows]


async def obtener(conn: asyncpg.Connection, reservacion_id: UUID) -> ReservacionesOut:
    row = await repo.obtener_por_id(conn, reservacion_id)
    if not row or not row["activo"]:
        raise NoEncontrado("Reservación")
    return ReservacionesOut.model_validate(dict(row))


async def crear(
    conn: asyncpg.Connection, body: ReservacionesCrear, actor_id: UUID | None = None
) -> ReservacionesOut:
    datos = body.model_dump()
    try:
        row = await repo.crear(conn, datos, creado_por=actor_id)
    except asyncpg.ForeignKeyViolationError:
        raise NoEncontrado("Sucursal, tipo de evento o paquete") from None
    return ReservacionesOut.model_validate(dict(row))


async def actualizar(
    conn: asyncpg.Connection,
    reservacion_id: UUID,
    body: ReservacionesUpdate,
    actor_id: UUID | None = None,
) -> ReservacionesOut:
    actual = await obtener(conn, reservacion_id)
    cambios = body.model_dump(exclude_unset=True)
    if not cambios:
        return actual
    row = await repo.actualizar(conn, reservacion_id, cambios, modificado_por=actor_id)
    assert row is not None  # garantizado por obtener() previo
    return ReservacionesOut.model_validate(dict(row))


async def eliminar(
    conn: asyncpg.Connection, reservacion_id: UUID, actor_id: UUID | None = None
) -> None:
    await obtener(conn, reservacion_id)
    await repo.desactivar(conn, reservacion_id, modificado_por=actor_id)
