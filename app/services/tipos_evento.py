from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NoEncontrado
from app.models.tipo_evento import TipoEventoModel
from app.schemas.tipos_evento import TiposEventoCreate, TiposEventoUpdate


async def listar(session: AsyncSession) -> list[TipoEventoModel]:
    result = await session.execute(
        select(TipoEventoModel).where(TipoEventoModel.activo == True)
    )
    return result.scalars().all()


async def obtener(session: AsyncSession, tipo_evento_id: UUID) -> TipoEventoModel:
    row = await session.get(TipoEventoModel, tipo_evento_id)
    if not row or not row.activo:
        raise NoEncontrado("Tipo de evento")
    return row


async def crear(session: AsyncSession, body: TiposEventoCreate) -> TipoEventoModel:
    tipo = TipoEventoModel(**body.model_dump(), creado=datetime.now(timezone.utc).isoformat())
    session.add(tipo)
    await session.commit()
    await session.refresh(tipo)
    return tipo


async def actualizar(session: AsyncSession, tipo_evento_id: UUID, body: TiposEventoUpdate) -> TipoEventoModel:
    row = await obtener(session, tipo_evento_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.modificado = datetime.now(timezone.utc).isoformat()
    await session.commit()
    await session.refresh(row)
    return row


async def eliminar(session: AsyncSession, tipo_evento_id: UUID) -> None:
    row = await obtener(session, tipo_evento_id)
    row.activo = False
    row.modificado = datetime.now(timezone.utc).isoformat()
    await session.commit()
