from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.dependencies import get_current_user
from app.schemas.reservaciones import ReservacionesCrear, ReservacionesOut, ReservacionesUpdate
import app.services.reservaciones as svc

router = APIRouter(prefix="/api/reservaciones", tags=["Reservaciones"])


@router.get("", response_model=list[ReservacionesOut])
async def listar_reservaciones(
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.listar(session)


@router.get("/{reservacion_id}", response_model=ReservacionesOut)
async def obtener_reservacion(
    reservacion_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.obtener(session, reservacion_id)


@router.post("", response_model=ReservacionesOut, status_code=status.HTTP_201_CREATED)
async def crear_reservacion(
    body: ReservacionesCrear,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.crear(session, body)


@router.patch("/{reservacion_id}", response_model=ReservacionesOut)
async def actualizar_reservacion(
    reservacion_id: UUID,
    body: ReservacionesUpdate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.actualizar(session, reservacion_id, body)


@router.delete("/{reservacion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_reservacion(
    reservacion_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    await svc.eliminar(session, reservacion_id)
