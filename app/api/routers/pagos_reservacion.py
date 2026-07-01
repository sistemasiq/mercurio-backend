from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

import app.services.pagos_reservacion as svc
from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.pagos_reservacion import (
    PagosReservacionCreate,
    PagosReservacionOut,
    PagosReservacionUpdate,
)

router = APIRouter(prefix="/api/pagos-reservacion", tags=["Pagos de Reservación"])


@router.get("", response_model=list[PagosReservacionOut])
async def listar_pagos(
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> list[PagosReservacionOut]:
    return await svc.listar_todos(conn)


@router.get("/reservacion/{reservacion_id}", response_model=list[PagosReservacionOut])
async def listar_pagos_reservacion(
    reservacion_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> list[PagosReservacionOut]:
    return await svc.listar_por_reservacion(conn, reservacion_id)


@router.get("/{pago_id}", response_model=PagosReservacionOut)
async def obtener_pago(
    pago_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> PagosReservacionOut:
    return await svc.obtener(conn, pago_id)


@router.post("", response_model=PagosReservacionOut, status_code=status.HTTP_201_CREATED)
async def crear_pago(
    body: PagosReservacionCreate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> PagosReservacionOut:
    return await svc.crear(conn, body)


@router.patch("/{pago_id}", response_model=PagosReservacionOut)
async def actualizar_pago(
    pago_id: UUID,
    body: PagosReservacionUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> PagosReservacionOut:
    return await svc.actualizar(conn, pago_id, body)


@router.delete("/{pago_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_pago(
    pago_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> None:
    await svc.eliminar(conn, pago_id)
