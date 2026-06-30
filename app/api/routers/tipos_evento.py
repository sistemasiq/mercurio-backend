from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

import app.services.tipos_evento as svc
from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.tipos_evento import TiposEventoCreate, TiposEventoOut, TiposEventoUpdate

router = APIRouter(prefix="/api/tipos-evento", tags=["Tipos de Evento"])


@router.get("", response_model=list[TiposEventoOut])
async def listar_tipos_evento(
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
):
    return await svc.listar(conn)


@router.get("/{tipo_evento_id}", response_model=TiposEventoOut)
async def obtener_tipo_evento(
    tipo_evento_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
):
    return await svc.obtener(conn, tipo_evento_id)


@router.post("", response_model=TiposEventoOut, status_code=status.HTTP_201_CREATED)
async def crear_tipo_evento(
    body: TiposEventoCreate,
    conn: asyncpg.Connection = Depends(get_db),
    user: TokenData = Depends(get_current_user),
):
    return await svc.crear(conn, body, user.sub)


@router.patch("/{tipo_evento_id}", response_model=TiposEventoOut)
async def actualizar_tipo_evento(
    tipo_evento_id: UUID,
    body: TiposEventoUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    user: TokenData = Depends(get_current_user),
):
    return await svc.actualizar(conn, tipo_evento_id, body, user.sub)


@router.delete("/{tipo_evento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_tipo_evento(
    tipo_evento_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    user: TokenData = Depends(get_current_user),
):
    await svc.eliminar(conn, tipo_evento_id, user.sub)
