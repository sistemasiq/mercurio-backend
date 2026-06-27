from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NoEncontrado
from app.models.pagos_reservacion import PagosReservacionModel
from app.schemas.pagos_reservacion import PagosReservacionCreate, PagosReservacionUpdate


async def listar(session: AsyncSession) -> list[PagosReservacionModel]:
    result = await session.execute(select(PagosReservacionModel))
    return result.scalars().all()


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
    pago = PagosReservacionModel(**body.model_dump(), fecha_pago=datetime.now(timezone.utc))
    session.add(pago)
    await session.commit()
    await session.refresh(pago)
    return pago


async def actualizar(session: AsyncSession, pago_id: UUID, body: PagosReservacionUpdate) -> PagosReservacionModel:
    row = await obtener(session, pago_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    await session.commit()
    await session.refresh(row)
    return row


async def eliminar(session: AsyncSession, pago_id: UUID) -> None:
    row = await obtener(session, pago_id)
    await session.delete(row)
    await session.commit()
