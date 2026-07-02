from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

import app.services.extras as svc
from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.extras import ExtrasCrear, ExtrasOut, ExtrasUpdate

router = APIRouter(prefix="/api/extras", tags=["Extras"])


@router.get("", response_model=list[ExtrasOut])
async def listar_extras(
    sucursal_id: UUID | None = None,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("extras:listar")),
) -> list[ExtrasOut]:
    return await svc.listar(conn, sucursal_id)


@router.get("/{extra_id}", response_model=ExtrasOut)
async def obtener_extra(
    extra_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("extras:ver")),
) -> ExtrasOut:
    return await svc.obtener(conn, extra_id)


@router.post("", response_model=ExtrasOut, status_code=status.HTTP_201_CREATED)
async def crear_extra(
    body: ExtrasCrear,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("extras:crear")),
) -> ExtrasOut:
    return await svc.crear(conn, body)


@router.patch("/{extra_id}", response_model=ExtrasOut)
async def actualizar_extra(
    extra_id: UUID,
    body: ExtrasUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("extras:editar")),
) -> ExtrasOut:
    return await svc.actualizar(conn, extra_id, body)


@router.delete("/{extra_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_extra(
    extra_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("extras:eliminar")),
) -> None:
    await svc.eliminar(conn, extra_id)
