from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NoEncontrado
from app.models.extras import ExtrasModel
from app.schemas.extras import ExtrasCrear, ExtrasUpdate


async def listar(session: AsyncSession, sucursal_id: UUID | None = None) -> list[ExtrasModel]:
    """Devuelve extras de una sucursal específica más los globales (sucursal_id=None)."""
    query = select(ExtrasModel).where(ExtrasModel.activo == True)
    if sucursal_id:
        query = query.where(
            (ExtrasModel.sucursal_id == sucursal_id) | (ExtrasModel.sucursal_id == None)
        )
    result = await session.execute(query)
    return result.scalars().all()


async def obtener(session: AsyncSession, extra_id: UUID) -> ExtrasModel:
    row = await session.get(ExtrasModel, extra_id)
    if not row or not row.activo:
        raise NoEncontrado("Extra")
    return row


async def crear(session: AsyncSession, body: ExtrasCrear) -> ExtrasModel:
    extra = ExtrasModel(**body.model_dump(), creado=datetime.now(timezone.utc).isoformat())
    session.add(extra)
    await session.commit()
    await session.refresh(extra)
    return extra


async def actualizar(session: AsyncSession, extra_id: UUID, body: ExtrasUpdate) -> ExtrasModel:
    row = await obtener(session, extra_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.modificado = datetime.now(timezone.utc).isoformat()
    await session.commit()
    await session.refresh(row)
    return row


async def eliminar(session: AsyncSession, extra_id: UUID) -> None:
    row = await obtener(session, extra_id)
    row.activo = False
    row.modificado = datetime.now(timezone.utc).isoformat()
    await session.commit()
