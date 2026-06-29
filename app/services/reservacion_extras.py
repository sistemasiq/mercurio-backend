from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NoEncontrado
from app.models.reservacion_extras import ReservacionExtrasModel
from app.schemas.reservacion_extras import ReservacionExtrasCreate, ReservacionExtrasUpdate


async def listar_por_reservacion(session: AsyncSession, reservacion_id: UUID) -> list[ReservacionExtrasModel]:
    result = await session.execute(
        select(ReservacionExtrasModel).where(ReservacionExtrasModel.reservacion_id == reservacion_id)
    )
    return result.scalars().all()


async def obtener(session: AsyncSession, reservacion_extra_id: UUID) -> ReservacionExtrasModel:
    row = await session.get(ReservacionExtrasModel, reservacion_extra_id)
    if not row:
        raise NoEncontrado("Extra de reservación")
    return row


async def crear(session: AsyncSession, body: ReservacionExtrasCreate) -> ReservacionExtrasModel:
    extra = ReservacionExtrasModel(**body.model_dump())
    session.add(extra)
    await session.commit()
    await session.refresh(extra)
    return extra


async def actualizar(session: AsyncSession, reservacion_extra_id: UUID, body: ReservacionExtrasUpdate) -> ReservacionExtrasModel:
    row = await obtener(session, reservacion_extra_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    await session.commit()
    await session.refresh(row)
    return row


async def eliminar(session: AsyncSession, reservacion_extra_id: UUID) -> None:
    row = await obtener(session, reservacion_extra_id)
    await session.delete(row)
    await session.commit()
