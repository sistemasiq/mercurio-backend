from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NoEncontrado
from app.models.metodos_pago import MetodosPagoModel
from app.schemas.metodos_pago import MetodosPagoCreate, MetodosPagoUpdate


async def listar(session: AsyncSession) -> list[MetodosPagoModel]:
    result = await session.execute(
        select(MetodosPagoModel).where(MetodosPagoModel.activo == True)
    )
    return result.scalars().all()


async def obtener(session: AsyncSession, metodo_pago_id: UUID) -> MetodosPagoModel:
    row = await session.get(MetodosPagoModel, metodo_pago_id)
    if not row or not row.activo:
        raise NoEncontrado("Método de pago")
    return row


async def crear(session: AsyncSession, body: MetodosPagoCreate) -> MetodosPagoModel:
    metodo = MetodosPagoModel(**body.model_dump())
    session.add(metodo)
    await session.commit()
    await session.refresh(metodo)
    return metodo


async def actualizar(session: AsyncSession, metodo_pago_id: UUID, body: MetodosPagoUpdate) -> MetodosPagoModel:
    row = await obtener(session, metodo_pago_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.modificado = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(row)
    return row


async def eliminar(session: AsyncSession, metodo_pago_id: UUID) -> None:
    row = await obtener(session, metodo_pago_id)
    row.activo = False
    row.modificado = datetime.now(timezone.utc)
    await session.commit()
