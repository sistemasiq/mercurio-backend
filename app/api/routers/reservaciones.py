from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

import app.services.reservaciones as svc
from app.api.deps import require_permission
from app.core.database import get_db
from app.core.scope import sucursal_scope
from app.schemas.auth import TokenData
from app.schemas.reservaciones import ReservacionesCrear, ReservacionesOut, ReservacionesUpdate

router = APIRouter(prefix="/api/reservaciones", tags=["Reservaciones"])


@router.get("", response_model=list[ReservacionesOut])
async def listar_reservaciones(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("reservaciones:listar")),
) -> list[ReservacionesOut]:
    return await svc.listar(conn, sucursal_scope(current_user))


@router.get("/{reservacion_id}", response_model=ReservacionesOut)
async def obtener_reservacion(
    reservacion_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("reservaciones:ver")),
) -> ReservacionesOut:
    return await svc.obtener(conn, reservacion_id)


@router.post("", response_model=ReservacionesOut, status_code=status.HTTP_201_CREATED)
async def crear_reservacion(
    body: ReservacionesCrear,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("reservaciones:crear")),
) -> ReservacionesOut:
    return await svc.crear(conn, body)


@router.patch("/{reservacion_id}", response_model=ReservacionesOut)
async def actualizar_reservacion(
    reservacion_id: UUID,
    body: ReservacionesUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("reservaciones:editar")),
) -> ReservacionesOut:
    return await svc.actualizar(conn, reservacion_id, body)


@router.delete("/{reservacion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_reservacion(
    reservacion_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("reservaciones:eliminar")),
) -> None:
    await svc.eliminar(conn, reservacion_id)
