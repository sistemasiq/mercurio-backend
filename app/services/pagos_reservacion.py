from datetime import UTC, datetime
from uuid import UUID

import asyncpg
from fastapi import HTTPException, status

from app.core.scope import sucursal_scope
from app.exceptions import NoEncontrado
from app.repositories import pagos_reservacion_repository, reservaciones_repository
from app.schemas.auth import TokenData
from app.schemas.pagos_reservacion import (
    PagosReservacionCreate,
    PagosReservacionOut,
    PagosReservacionUpdate,
)


async def listar_todos(
    conn: asyncpg.Connection, scope: str | None = None
) -> list[PagosReservacionOut]:
    rows = await pagos_reservacion_repository.listar_todos(conn, scope)
    return [PagosReservacionOut.model_validate(r) for r in rows]


async def listar_por_reservacion(
    conn: asyncpg.Connection, reservacion_id: UUID, current_user: TokenData
) -> list[PagosReservacionOut]:
    reservacion = await reservaciones_repository.obtener(conn, reservacion_id)
    if not reservacion:
        raise NoEncontrado("Reservación")

    scope = sucursal_scope(current_user)
    if scope is not None and str(reservacion["sucursal_id"]) != scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede consultar pagos de reservaciones de otra sucursal.",
        )

    rows = await pagos_reservacion_repository.listar_por_reservacion(conn, reservacion_id)
    return [PagosReservacionOut.model_validate(r) for r in rows]


async def obtener(conn: asyncpg.Connection, pago_id: UUID) -> PagosReservacionOut:
    row = await pagos_reservacion_repository.obtener(conn, pago_id)
    if not row:
        raise NoEncontrado("Pago")
    return PagosReservacionOut.model_validate(row)


async def crear(conn: asyncpg.Connection, body: PagosReservacionCreate) -> PagosReservacionOut:
    row = await pagos_reservacion_repository.crear(
        conn,
        reservacion_id=body.reservacion_id,
        metodo_pago_id=body.metodo_pago_id,
        monto=body.monto,
        fecha_pago=datetime.now(UTC),
        notas=body.notas,
    )
    return PagosReservacionOut.model_validate(row)


async def actualizar(
    conn: asyncpg.Connection, pago_id: UUID, body: PagosReservacionUpdate
) -> PagosReservacionOut:
    await obtener(conn, pago_id)
    updates = body.model_dump(exclude_unset=True)
    row = await pagos_reservacion_repository.actualizar(conn, pago_id, updates)
    if not row:
        raise NoEncontrado("Pago")
    return PagosReservacionOut.model_validate(row)


async def eliminar(conn: asyncpg.Connection, pago_id: UUID) -> None:
    await obtener(conn, pago_id)
    await pagos_reservacion_repository.eliminar(conn, pago_id)
