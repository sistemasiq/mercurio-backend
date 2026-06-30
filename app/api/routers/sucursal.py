from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

import app.services.sucursal as svc
from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.sucursal import SucursalCreate, SucursalOut, SucursalUpdate

router = APIRouter(prefix="/api/sucursales", tags=["Sucursales"])


@router.get("", response_model=list[SucursalOut])
async def listar_sucursales(
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
):
    return await svc.listar(conn)


@router.get("/{sucursal_id}", response_model=SucursalOut)
async def obtener_sucursal(
    sucursal_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
):
    return await svc.obtener(conn, sucursal_id)


@router.post("", response_model=SucursalOut, status_code=status.HTTP_201_CREATED)
async def crear_sucursal(
    body: SucursalCreate,
    conn: asyncpg.Connection = Depends(get_db),
    user: TokenData = Depends(get_current_user),
):
    return await svc.crear(conn, body, user.sub)


@router.patch("/{sucursal_id}", response_model=SucursalOut)
async def actualizar_sucursal(
    sucursal_id: UUID,
    body: SucursalUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    user: TokenData = Depends(get_current_user),
):
    return await svc.actualizar(conn, sucursal_id, body, user.sub)


@router.delete("/{sucursal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_sucursal(
    sucursal_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    user: TokenData = Depends(get_current_user),
):
    await svc.eliminar(conn, sucursal_id, user.sub)
