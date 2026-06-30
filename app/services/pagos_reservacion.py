from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado
from app.repositories import pagos_reservacion as repo
from app.schemas.pagos_reservacion import (
    PagosReservacionCreate,
    PagosReservacionOut,
    PagosReservacionUpdate,
)


async def listar(conn: asyncpg.Connection) -> list[PagosReservacionOut]:
    rows = await repo.listar(conn)
    return [PagosReservacionOut.model_validate(dict(r)) for r in rows]


async def listar_por_reservacion(
    conn: asyncpg.Connection, reservacion_id: UUID
) -> list[PagosReservacionOut]:
    rows = await repo.listar_por_reservacion(conn, reservacion_id)
    return [PagosReservacionOut.model_validate(dict(r)) for r in rows]


async def obtener(conn: asyncpg.Connection, pago_id: UUID) -> PagosReservacionOut:
    row = await repo.obtener_por_id(conn, pago_id)
    if not row:
        raise NoEncontrado("Pago")
    return PagosReservacionOut.model_validate(dict(row))


async def crear(
    conn: asyncpg.Connection,
    body: PagosReservacionCreate,
    actor_id: UUID | None = None,
) -> PagosReservacionOut:
    try:
        row = await repo.crear(
            conn,
            reservacion_id=body.reservacion_id,
            metodo_pago_id=body.metodo_pago_id,
            monto=body.monto,
            notas=body.notas,
            creado_por=actor_id,
        )
    except asyncpg.ForeignKeyViolationError:
        raise NoEncontrado("Reservación o método de pago") from None
    return PagosReservacionOut.model_validate(dict(row))


async def actualizar(
    conn: asyncpg.Connection, pago_id: UUID, body: PagosReservacionUpdate
) -> PagosReservacionOut:
    actual = await obtener(conn, pago_id)
    cambios = body.model_dump(exclude_unset=True)
    if not cambios:
        return actual
    row = await repo.actualizar(conn, pago_id, cambios)
    assert row is not None  # garantizado por obtener() previo
    return PagosReservacionOut.model_validate(dict(row))


async def eliminar(conn: asyncpg.Connection, pago_id: UUID) -> None:
    resultado = await repo.eliminar(conn, pago_id)
    if resultado.endswith("0"):
        raise NoEncontrado("Pago")
