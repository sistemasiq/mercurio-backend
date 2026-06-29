from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.dependencies import get_current_user
from app.schemas.tipos_evento import TiposEventoCreate, TiposEventoOut, TiposEventoUpdate
import app.services.tipos_evento as svc

router = APIRouter(prefix="/api/tipos-evento", tags=["Tipos de Evento"])


@router.get("", response_model=list[TiposEventoOut])
async def listar_tipos_evento(
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.listar(session)


@router.get("/{tipo_evento_id}", response_model=TiposEventoOut)
async def obtener_tipo_evento(
    tipo_evento_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.obtener(session, tipo_evento_id)


@router.post("", response_model=TiposEventoOut, status_code=status.HTTP_201_CREATED)
async def crear_tipo_evento(
    body: TiposEventoCreate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.crear(session, body)


@router.patch("/{tipo_evento_id}", response_model=TiposEventoOut)
async def actualizar_tipo_evento(
    tipo_evento_id: UUID,
    body: TiposEventoUpdate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.actualizar(session, tipo_evento_id, body)


@router.delete("/{tipo_evento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_tipo_evento(
    tipo_evento_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    await svc.eliminar(session, tipo_evento_id)
