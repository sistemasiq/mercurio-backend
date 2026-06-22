from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.dependencies import get_current_user
from app.schemas.extras import ExtrasCrear, ExtrasOut, ExtrasUpdate
import app.services.extras as svc

router = APIRouter(prefix="/api/extras", tags=["Extras"])


@router.get("", response_model=list[ExtrasOut])
async def listar_extras(
    sucursal_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.listar(session, sucursal_id)


@router.get("/{extra_id}", response_model=ExtrasOut)
async def obtener_extra(
    extra_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.obtener(session, extra_id)


@router.post("", response_model=ExtrasOut, status_code=status.HTTP_201_CREATED)
async def crear_extra(
    body: ExtrasCrear,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.crear(session, body)


@router.patch("/{extra_id}", response_model=ExtrasOut)
async def actualizar_extra(
    extra_id: UUID,
    body: ExtrasUpdate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.actualizar(session, extra_id, body)


@router.delete("/{extra_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_extra(
    extra_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    await svc.eliminar(session, extra_id)
