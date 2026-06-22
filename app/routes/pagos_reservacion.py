from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.dependencies import get_current_user
from app.schemas.pagos_reservacion import PagosReservacionCreate, PagosReservacionOut, PagosReservacionUpdate
import app.services.pagos_reservacion as svc

router = APIRouter(prefix="/api/pagos-reservacion", tags=["Pagos de Reservación"])


@router.get("/reservacion/{reservacion_id}", response_model=list[PagosReservacionOut])
async def listar_pagos_reservacion(
    reservacion_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.listar_por_reservacion(session, reservacion_id)


@router.get("/{pago_id}", response_model=PagosReservacionOut)
async def obtener_pago(
    pago_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.obtener(session, pago_id)


@router.post("", response_model=PagosReservacionOut, status_code=status.HTTP_201_CREATED)
async def crear_pago(
    body: PagosReservacionCreate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.crear(session, body)


@router.patch("/{pago_id}", response_model=PagosReservacionOut)
async def actualizar_pago(
    pago_id: UUID,
    body: PagosReservacionUpdate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.actualizar(session, pago_id, body)


@router.delete("/{pago_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_pago(
    pago_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    await svc.eliminar(session, pago_id)
