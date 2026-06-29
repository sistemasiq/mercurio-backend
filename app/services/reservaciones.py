from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NoEncontrado
from app.models.reservaciones import ReservacionModel
from app.schemas.reservaciones import ReservacionesCrear, ReservacionesUpdate


async def listar(session: AsyncSession, sucursal_id: UUID | None = None) -> list[ReservacionModel]:
    query = select(ReservacionModel).where(ReservacionModel.activo == True)
    if sucursal_id:
        query = query.where(ReservacionModel.sucursal_id == sucursal_id)
    result = await session.execute(query)
    return result.scalars().all()


async def obtener(session: AsyncSession, reservacion_id: UUID) -> ReservacionModel:
    row = await session.get(ReservacionModel, reservacion_id)
    if not row or not row.activo:
        raise NoEncontrado("Reservación")
    return row


async def crear(session: AsyncSession, body: ReservacionesCrear) -> ReservacionModel:
    reservacion = ReservacionModel(**body.model_dump())
    session.add(reservacion)
    await session.commit()
    await session.refresh(reservacion)
    return reservacion


async def actualizar(session: AsyncSession, reservacion_id: UUID, body: ReservacionesUpdate) -> ReservacionModel:
    row = await obtener(session, reservacion_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.modificado = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(row)
    return row


async def eliminar(session: AsyncSession, reservacion_id: UUID) -> None:
    row = await obtener(session, reservacion_id)
    row.activo = False
    row.modificado = datetime.now(timezone.utc)
    await session.commit()
