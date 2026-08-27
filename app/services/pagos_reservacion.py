from datetime import UTC, datetime
from uuid import UUID

import asyncpg
from fastapi import HTTPException, status

from app.core.scope import sucursal_scope
from app.exceptions import NoEncontrado
from app.repositories import pagos_reservacion_repository, reservaciones_repository
from app.repositories.caja_repository import registrar_movimiento_caja
from app.schemas.auth import TokenData
from app.schemas.pagos_reservacion import (
    PagosReservacionCreate,
    PagosReservacionOut,
    PagosReservacionUpdate,
)
from app.services import lealtad_service


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


async def crear(
    conn: asyncpg.Connection,
    body: PagosReservacionCreate,
    usuario_id: UUID,
    apertura_caja_id: str,
) -> PagosReservacionOut:
    row = await pagos_reservacion_repository.crear(
        conn,
        reservacion_id=body.reservacion_id,
        metodo_pago_id=body.metodo_pago_id,
        monto=body.monto,
        fecha_pago=datetime.now(UTC),
        notas=body.notas,
        # Sin esto la columna quedaba siempre en NULL y el historial no podía
        # decir quién cobró el evento, a diferencia de las ventas de mostrador.
        creado_por=usuario_id,
    )

    await registrar_movimiento_caja(
        conn,
        apertura_caja_id=apertura_caja_id,
        tipo_movimiento="R",
        referencia_id=str(row["id"]),
        metodo_pago_id=str(body.metodo_pago_id),
        monto=body.monto,
        creado_por=str(usuario_id),
    )

    reservacion = await reservaciones_repository.obtener(conn, body.reservacion_id)
    celular = (reservacion["telefono_cliente"] or "").strip() if reservacion else ""
    if reservacion and celular:
        await lealtad_service.otorgar_puntos(
            conn,
            reservacion["sucursal_id"],
            celular,
            body.monto,
            usuario_id,
            reservacion_id=body.reservacion_id,
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
