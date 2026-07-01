from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

import app.services.paquetes as svc
from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.paquetes import PaquetesCreate, PaquetesOut, PaquetesUpdate

router = APIRouter(prefix="/api/paquetes", tags=["Paquetes"])


@router.get("", response_model=list[PaquetesOut])
async def listar_paquetes(
    sucursal_id: UUID | None = None,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> list[PaquetesOut]:
    return await svc.listar(conn, sucursal_id)


@router.get("/{paquete_id}", response_model=PaquetesOut)
async def obtener_paquete(
    paquete_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> PaquetesOut:
    return await svc.obtener(conn, paquete_id)


@router.post("", response_model=PaquetesOut, status_code=status.HTTP_201_CREATED)
async def crear_paquete(
    body: PaquetesCreate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> PaquetesOut:
    return await svc.crear(conn, body)


@router.patch("/{paquete_id}", response_model=PaquetesOut)
async def actualizar_paquete(
    paquete_id: UUID,
    body: PaquetesUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> PaquetesOut:
    return await svc.actualizar(conn, paquete_id, body)


@router.delete("/{paquete_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_paquete(
    paquete_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> None:
    await svc.eliminar(conn, paquete_id)
