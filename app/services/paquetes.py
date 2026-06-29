from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NoEncontrado
from app.models.paquetes import PaqueteModel
from app.schemas.paquetes import PaquetesCreate, PaquetesUpdate


async def listar(session: AsyncSession, sucursal_id: UUID | None = None) -> list[PaqueteModel]:
    query = select(PaqueteModel).where(PaqueteModel.activo == True)
    if sucursal_id:
        query = query.where(PaqueteModel.sucursal_id == sucursal_id)
    result = await session.execute(query)
    return result.scalars().all()


async def obtener(session: AsyncSession, paquete_id: UUID) -> PaqueteModel:
    row = await session.get(PaqueteModel, paquete_id)
    if not row or not row.activo:
        raise NoEncontrado("Paquete")
    return row


async def crear(session: AsyncSession, body: PaquetesCreate) -> PaqueteModel:
    paquete = PaqueteModel(**body.model_dump())
    session.add(paquete)
    await session.commit()
    await session.refresh(paquete)
    return paquete


async def actualizar(session: AsyncSession, paquete_id: UUID, body: PaquetesUpdate) -> PaqueteModel:
    row = await obtener(session, paquete_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.modificado = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(row)
    return row


async def eliminar(session: AsyncSession, paquete_id: UUID) -> None:
    row = await obtener(session, paquete_id)
    row.activo = False
    row.modificado = datetime.now(timezone.utc)
    await session.commit()
