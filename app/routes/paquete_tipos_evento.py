from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.dependencies import get_current_user
from app.schemas.paquete_tipos_evento import PaqueteTiposEventoCreate, PaqueteTiposEventoOut
import app.services.paquete_tipos_evento as svc

router = APIRouter(prefix="/api/paquete-tipos-evento", tags=["Paquete Tipos de Evento"])


@router.get("/{paquete_id}", response_model=list[PaqueteTiposEventoOut])
async def listar_por_paquete(
    paquete_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.listar_por_paquete(session, paquete_id)


@router.post("", response_model=PaqueteTiposEventoOut, status_code=status.HTTP_201_CREATED)
async def agregar_tipo_evento(
    body: PaqueteTiposEventoCreate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.agregar(session, body)


@router.delete("/{paquete_id}/{tipo_evento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_tipo_evento(
    paquete_id: UUID,
    tipo_evento_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    await svc.eliminar(session, paquete_id, tipo_evento_id)
