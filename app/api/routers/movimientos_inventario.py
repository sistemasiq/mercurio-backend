"""
app/api/routers/movimientos_inventario.py
Router de movimientos de inventario (ajustes manuales e historial) — solo
delega al service. Archivo propio aunque sea sub-recurso de insumos, mismo
criterio que producto_insumos.py respecto de productos.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.movimiento_inventario import MovimientoInventarioOut, MovimientoManualCreate
from app.services import inventario_service

router = APIRouter(prefix="/api/insumos", tags=["Movimientos de Inventario"])


@router.get("/{insumo_id}/movimientos", response_model=list[MovimientoInventarioOut])
async def listar_movimientos(
    insumo_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:ver_movimientos")),
) -> list[MovimientoInventarioOut]:
    return await inventario_service.listar_movimientos(conn, insumo_id)


@router.post(
    "/{insumo_id}/movimientos",
    response_model=MovimientoInventarioOut,
    status_code=status.HTTP_201_CREATED,
)
async def registrar_movimiento(
    insumo_id: UUID,
    body: MovimientoManualCreate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("inventario:registrar_movimiento")),
) -> MovimientoInventarioOut:
    return await inventario_service.registrar_ajuste_manual(
        conn, insumo_id, body, UUID(current_user.sub)
    )
