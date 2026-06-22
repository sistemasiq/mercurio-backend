from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NoEncontrado
from app.models.pagos_reservacion import PagosReservacionModel
from app.models.reservaciones import ReservacionModel
from app.schemas.pagos_reservacion import PagosReservacionCreate, PagosReservacionUpdate


async def listar_por_reservacion(session: AsyncSession, reservacion_id: UUID) -> list[PagosReservacionModel]:
    result = await session.execute(
        select(PagosReservacionModel).where(PagosReservacionModel.reservacion_id == reservacion_id)
    )
    return result.scalars().all()


async def obtener(session: AsyncSession, pago_id: UUID) -> PagosReservacionModel:
    row = await session.get(PagosReservacionModel, pago_id)
    if not row:
        raise NoEncontrado("Pago")
    return row


async def crear(session: AsyncSession, body: PagosReservacionCreate) -> PagosReservacionModel:
    now = datetime.now(timezone.utc)
    pago = PagosReservacionModel(**body.model_dump(), fecha_pago=now)
    session.add(pago)

    # descuenta el monto del saldo de la reservación
    reservacion = await session.get(ReservacionModel, body.reservacion_id)
    if reservacion:
        reservacion.saldo_pendiente -= body.monto
        reservacion.modificado = now.isoformat()

    await session.commit()
    await session.refresh(pago)
    return pago


async def actualizar(session: AsyncSession, pago_id: UUID, body: PagosReservacionUpdate) -> PagosReservacionModel:
    row = await obtener(session, pago_id)
    monto_anterior = row.monto
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)

    # ajusta saldo si cambió el monto
    if body.monto is not None:
        reservacion = await session.get(ReservacionModel, row.reservacion_id)
        if reservacion:
            reservacion.saldo_pendiente += monto_anterior - body.monto
            reservacion.modificado = datetime.now(timezone.utc).isoformat()

    await session.commit()
    await session.refresh(row)
    return row


async def eliminar(session: AsyncSession, pago_id: UUID) -> None:
    row = await obtener(session, pago_id)

    # regresa el monto al saldo de la reservación
    reservacion = await session.get(ReservacionModel, row.reservacion_id)
    if reservacion:
        reservacion.saldo_pendiente += row.monto
        reservacion.modificado = datetime.now(timezone.utc).isoformat()

    await session.delete(row)
    await session.commit()
