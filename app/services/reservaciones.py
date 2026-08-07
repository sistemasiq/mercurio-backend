from uuid import UUID

import asyncpg

from app.exceptions import DatosInvalidos, NoEncontrado
from app.repositories import reservaciones_repository,registros
from app.schemas.reservaciones import ReservacionesCrear, ReservacionesOut, ReservacionesUpdate, EventoDelDiaOut


async def listar(conn: asyncpg.Connection, scope: str | None = None) -> list[ReservacionesOut]:
    rows = await reservaciones_repository.listar(conn, scope)
    return [ReservacionesOut.model_validate(r) for r in rows]

async def obtener_evento_cercano(conn: asyncpg.Connection, sucursal_id: UUID) -> EventoDelDiaOut | None:
    row = await reservaciones_repository.obtener_evento_mas_cercano(conn, sucursal_id)
    if not row:
        return None

    registro_existente = await registros.exists_registro_by_reservacion_id(conn, row["id"])
    if registro_existente:
        return None

    return EventoDelDiaOut.model_validate(row)

async def obtener(conn: asyncpg.Connection, reservacion_id: UUID) -> ReservacionesOut:
    row = await reservaciones_repository.obtener(conn, reservacion_id)
    if not row or not row["activo"]:
        raise NoEncontrado("Reservación")
    return ReservacionesOut.model_validate(row)


async def crear(conn: asyncpg.Connection, body: ReservacionesCrear) -> ReservacionesOut:
    data = body.model_dump()
    row = await reservaciones_repository.crear(conn, data)
    return ReservacionesOut.model_validate(row)


async def actualizar(
    conn: asyncpg.Connection, reservacion_id: UUID, body: ReservacionesUpdate
) -> ReservacionesOut:
    actual = await obtener(conn, reservacion_id)
    updates = body.model_dump(exclude_unset=True)
    hora_inicio = updates.get("hora_inicio", actual.hora_inicio)
    hora_fin = updates.get("hora_fin", actual.hora_fin)
    if hora_fin <= hora_inicio:
        raise DatosInvalidos("hora_fin debe ser mayor a hora_inicio")
    row = await reservaciones_repository.actualizar(conn, reservacion_id, updates)
    if not row:
        raise NoEncontrado("Reservación")
    return ReservacionesOut.model_validate(row)


async def eliminar(conn: asyncpg.Connection, reservacion_id: UUID) -> None:
    await obtener(conn, reservacion_id)
    await reservaciones_repository.eliminar(conn, reservacion_id)
