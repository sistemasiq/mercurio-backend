"""
app/api/routers/presentaciones_insumo.py
Router de presentaciones de compra de un insumo — solo delega al service.
SAD §3.2 / Regla 11.4: el router nunca accede a un repository ni escribe SQL.
Archivo propio aunque sea sub-recurso de insumos, mismo criterio que
producto_insumos.py / movimientos_inventario.py.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.presentacion_insumo import PresentacionCrear, PresentacionOut, PresentacionUpdate
from app.services import presentacion_insumo_service

router = APIRouter(prefix="/api/insumos", tags=["Presentaciones de Insumo"])


@router.get("/{insumo_id}/presentaciones", response_model=list[PresentacionOut])
async def listar_presentaciones(
    insumo_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:ver")),
) -> list[PresentacionOut]:
    return await presentacion_insumo_service.listar(conn, insumo_id)


@router.post(
    "/{insumo_id}/presentaciones",
    response_model=PresentacionOut,
    status_code=status.HTTP_201_CREATED,
)
async def crear_presentacion(
    insumo_id: UUID,
    body: PresentacionCrear,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("inventario:gestionar_insumos")),
) -> PresentacionOut:
    return await presentacion_insumo_service.crear(conn, insumo_id, body, current_user)


@router.patch("/{insumo_id}/presentaciones/{presentacion_id}", response_model=PresentacionOut)
async def actualizar_presentacion(
    insumo_id: UUID,
    presentacion_id: UUID,
    body: PresentacionUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("inventario:gestionar_insumos")),
) -> PresentacionOut:
    return await presentacion_insumo_service.actualizar(conn, presentacion_id, body, current_user)


@router.delete(
    "/{insumo_id}/presentaciones/{presentacion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def eliminar_presentacion(
    insumo_id: UUID,
    presentacion_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:eliminar_insumo")),
) -> None:
    await presentacion_insumo_service.eliminar(conn, presentacion_id)
