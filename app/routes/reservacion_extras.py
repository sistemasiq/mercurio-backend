from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.dependencies import get_current_user
from app.schemas.reservacion_extras import ReservacionExtrasCreate, ReservacionExtrasOut, ReservacionExtrasUpdate
import app.services.reservacion_extras as svc

router = APIRouter(prefix="/api/reservacion-extras", tags=["Reservación Extras"])


@router.get("/reservacion/{reservacion_id}", response_model=list[ReservacionExtrasOut])
async def listar_por_reservacion(
    reservacion_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.listar_por_reservacion(session, reservacion_id)


@router.get("/{reservacion_extra_id}", response_model=ReservacionExtrasOut)
async def obtener_reservacion_extra(
    reservacion_extra_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.obtener(session, reservacion_extra_id)


@router.post("", response_model=ReservacionExtrasOut, status_code=status.HTTP_201_CREATED)
async def crear_reservacion_extra(
    body: ReservacionExtrasCreate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.crear(session, body)


@router.patch("/{reservacion_extra_id}", response_model=ReservacionExtrasOut)
async def actualizar_reservacion_extra(
    reservacion_extra_id: UUID,
    body: ReservacionExtrasUpdate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.actualizar(session, reservacion_extra_id, body)


@router.delete("/{reservacion_extra_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_reservacion_extra(
    reservacion_extra_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    await svc.eliminar(session, reservacion_extra_id)
