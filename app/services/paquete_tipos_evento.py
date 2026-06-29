from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NoEncontrado
from app.models.paquete_tipos_evento import PaqueteTipoEventoModel
from app.schemas.paquete_tipos_evento import PaqueteTiposEventoCreate


async def listar_por_paquete(session: AsyncSession, paquete_id: UUID) -> list[PaqueteTipoEventoModel]:
    result = await session.execute(
        select(PaqueteTipoEventoModel).where(PaqueteTipoEventoModel.paquete_id == paquete_id)
    )
    return result.scalars().all()


async def agregar(session: AsyncSession, body: PaqueteTiposEventoCreate) -> PaqueteTipoEventoModel:
    fila = PaqueteTipoEventoModel(paquete_id=body.paquete_id, tipo_evento_id=body.tipo_evento_id)
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


async def eliminar(session: AsyncSession, paquete_id: UUID, tipo_evento_id: UUID) -> None:
    result = await session.execute(
        select(PaqueteTipoEventoModel).where(
            PaqueteTipoEventoModel.paquete_id == paquete_id,
            PaqueteTipoEventoModel.tipo_evento_id == tipo_evento_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NoEncontrado("Relación paquete-tipo de evento")
    await session.delete(row)
    await session.commit()
