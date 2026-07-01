from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

import app.services.reservacion_extras as svc
from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.reservacion_extras import (
    ReservacionExtrasCreate,
    ReservacionExtrasOut,
    ReservacionExtrasUpdate,
)

router = APIRouter(prefix="/api/reservacion-extras", tags=["Reservación Extras"])


@router.get("/reservacion/{reservacion_id}", response_model=list[ReservacionExtrasOut])
async def listar_por_reservacion(
    reservacion_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> list[ReservacionExtrasOut]:
    return await svc.listar_por_reservacion(conn, reservacion_id)


@router.get("/{reservacion_extra_id}", response_model=ReservacionExtrasOut)
async def obtener_reservacion_extra(
    reservacion_extra_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> ReservacionExtrasOut:
    return await svc.obtener(conn, reservacion_extra_id)


@router.post("", response_model=ReservacionExtrasOut, status_code=status.HTTP_201_CREATED)
async def crear_reservacion_extra(
    body: ReservacionExtrasCreate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> ReservacionExtrasOut:
    return await svc.crear(conn, body)


@router.patch("/{reservacion_extra_id}", response_model=ReservacionExtrasOut)
async def actualizar_reservacion_extra(
    reservacion_extra_id: UUID,
    body: ReservacionExtrasUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> ReservacionExtrasOut:
    return await svc.actualizar(conn, reservacion_extra_id, body)


@router.delete("/{reservacion_extra_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_reservacion_extra(
    reservacion_extra_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> None:
    await svc.eliminar(conn, reservacion_extra_id)
