"""
app/api/routers/producto_insumos.py
Router de la receta (BOM) de productos — solo delega al service.
SAD §3.2 / Regla 11.4: el router nunca accede a un repository ni escribe SQL.
Archivo propio aunque sea sub-recurso de productos, mismo criterio que
paquete_tipos_evento.py respecto de paquetes.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.receta_producto import RecetaItemOut, RecetaItemUpdate
from app.services import receta_producto_service

router = APIRouter(prefix="/api/productos", tags=["Receta de Productos"])


@router.get("/{producto_id}/receta", response_model=list[RecetaItemOut])
async def listar_receta(
    producto_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:ver")),
) -> list[RecetaItemOut]:
    return await receta_producto_service.listar(conn, producto_id)


@router.put("/{producto_id}/receta/{insumo_id}", response_model=RecetaItemOut)
async def upsert_receta_item(
    producto_id: UUID,
    insumo_id: UUID,
    body: RecetaItemUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:gestionar_productos")),
) -> RecetaItemOut:
    return await receta_producto_service.upsert(conn, producto_id, insumo_id, body)


@router.delete(
    "/{producto_id}/receta/{insumo_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def eliminar_receta_item(
    producto_id: UUID,
    insumo_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:gestionar_productos")),
) -> None:
    await receta_producto_service.eliminar(conn, producto_id, insumo_id)
