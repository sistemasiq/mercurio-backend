from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.dependencies import get_current_user
from app.schemas.paquetes import PaquetesCreate, PaquetesOut, PaquetesUpdate
import app.services.paquetes as svc

router = APIRouter(prefix="/api/paquetes", tags=["Paquetes"])


@router.get("", response_model=list[PaquetesOut])
async def listar_paquetes(
    sucursal_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.listar(session, sucursal_id)


@router.get("/{paquete_id}", response_model=PaquetesOut)
async def obtener_paquete(
    paquete_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.obtener(session, paquete_id)


@router.post("", response_model=PaquetesOut, status_code=status.HTTP_201_CREATED)
async def crear_paquete(
    body: PaquetesCreate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.crear(session, body)


@router.patch("/{paquete_id}", response_model=PaquetesOut)
async def actualizar_paquete(
    paquete_id: UUID,
    body: PaquetesUpdate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.actualizar(session, paquete_id, body)


@router.delete("/{paquete_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_paquete(
    paquete_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    await svc.eliminar(session, paquete_id)
