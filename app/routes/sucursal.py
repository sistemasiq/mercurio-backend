from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.dependencies import get_current_user
from app.schemas.sucursal import SucursalCreate, SucursalOut, SucursalUpdate
import app.services.sucursal as svc

router = APIRouter(prefix="/api/sucursales", tags=["Sucursales"])


@router.get("", response_model=list[SucursalOut])
async def listar_sucursales(
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.listar(session)


@router.get("/{sucursal_id}", response_model=SucursalOut)
async def obtener_sucursal(
    sucursal_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.obtener(session, sucursal_id)


@router.post("", response_model=SucursalOut, status_code=status.HTTP_201_CREATED)
async def crear_sucursal(
    body: SucursalCreate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.crear(session, body)


@router.patch("/{sucursal_id}", response_model=SucursalOut)
async def actualizar_sucursal(
    sucursal_id: UUID,
    body: SucursalUpdate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.actualizar(session, sucursal_id, body)


@router.delete("/{sucursal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_sucursal(
    sucursal_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    await svc.eliminar(session, sucursal_id)
