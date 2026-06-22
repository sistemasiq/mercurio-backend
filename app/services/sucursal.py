from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NoEncontrado
from app.models.sucursal import SucursalModel
from app.schemas.sucursal import SucursalCreate, SucursalUpdate


async def listar(session: AsyncSession) -> list[SucursalModel]:
    result = await session.execute(
        select(SucursalModel).where(SucursalModel.activo == True)
    )
    return result.scalars().all()


async def obtener(session: AsyncSession, sucursal_id: UUID) -> SucursalModel:
    row = await session.get(SucursalModel, sucursal_id)
    if not row or not row.activo:
        raise NoEncontrado("Sucursal")
    return row


async def crear(session: AsyncSession, body: SucursalCreate) -> SucursalModel:
    sucursal = SucursalModel(**body.model_dump(), creado=datetime.now(timezone.utc).isoformat())
    session.add(sucursal)
    await session.commit()
    await session.refresh(sucursal)
    return sucursal


async def actualizar(session: AsyncSession, sucursal_id: UUID, body: SucursalUpdate) -> SucursalModel:
    row = await obtener(session, sucursal_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.modificado = datetime.now(timezone.utc).isoformat()
    await session.commit()
    await session.refresh(row)
    return row


async def eliminar(session: AsyncSession, sucursal_id: UUID) -> None:
    row = await obtener(session, sucursal_id)
    row.activo = False
    row.modificado = datetime.now(timezone.utc).isoformat()
    await session.commit()
