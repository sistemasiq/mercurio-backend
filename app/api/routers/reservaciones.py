from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

import app.services.reservaciones as svc
from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.reservaciones import (
    ReservacionesCrear,
    ReservacionesOut,
    ReservacionesUpdate,
)

router = APIRouter(prefix="/api/reservaciones", tags=["Reservaciones"])


@router.get("", response_model=list[ReservacionesOut])
async def listar_reservaciones(
    sucursal_id: UUID | None = None,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
):
    return await svc.listar(conn, sucursal_id)


@router.get("/{reservacion_id}", response_model=ReservacionesOut)
async def obtener_reservacion(
    reservacion_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
):
    return await svc.obtener(conn, reservacion_id)


@router.post("", response_model=ReservacionesOut, status_code=status.HTTP_201_CREATED)
async def crear_reservacion(
    body: ReservacionesCrear,
    conn: asyncpg.Connection = Depends(get_db),
    user: TokenData = Depends(get_current_user),
):
    return await svc.crear(conn, body, user.sub)


@router.patch("/{reservacion_id}", response_model=ReservacionesOut)
async def actualizar_reservacion(
    reservacion_id: UUID,
    body: ReservacionesUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    user: TokenData = Depends(get_current_user),
):
    return await svc.actualizar(conn, reservacion_id, body, user.sub)


@router.delete("/{reservacion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_reservacion(
    reservacion_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    user: TokenData = Depends(get_current_user),
):
    await svc.eliminar(conn, reservacion_id, user.sub)
