"""
app/api/routers/compras.py
Router de compras a proveedor — solo delega al service.
SAD §3.2 / Regla 11.4: el router nunca accede a un repository ni escribe SQL.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.compra import CompraCrear, CompraOut, CompraUpdate
from app.services import compra_service

router = APIRouter(prefix="/api/compras", tags=["Compras"])


@router.get("", response_model=list[CompraOut])
async def listar_compras(
    sucursal_id: UUID | None = None,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:ver")),
) -> list[CompraOut]:
    return await compra_service.listar(conn, sucursal_id)


@router.get("/{compra_id}", response_model=CompraOut)
async def obtener_compra(
    compra_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:ver")),
) -> CompraOut:
    return await compra_service.obtener(conn, compra_id)


@router.post("", response_model=CompraOut, status_code=status.HTTP_201_CREATED)
async def crear_compra(
    body: CompraCrear,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("inventario:gestionar_compras")),
) -> CompraOut:
    return await compra_service.crear(conn, body, UUID(current_user.sub))


@router.patch("/{compra_id}", response_model=CompraOut)
async def actualizar_compra(
    compra_id: UUID,
    body: CompraUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:gestionar_compras")),
) -> CompraOut:
    return await compra_service.actualizar(conn, compra_id, body)


@router.post("/{compra_id}/recibir", response_model=CompraOut)
async def recibir_compra(
    compra_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("inventario:gestionar_compras")),
) -> CompraOut:
    return await compra_service.recibir(conn, compra_id, UUID(current_user.sub))


@router.post("/{compra_id}/cancelar", response_model=CompraOut)
async def cancelar_compra(
    compra_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:gestionar_compras")),
) -> CompraOut:
    return await compra_service.cancelar(conn, compra_id)
