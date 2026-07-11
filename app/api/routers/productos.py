"""
app/api/routers/productos.py
Router de productos — solo delega al service.
SAD §3.2 / Regla 11.4: el router nunca accede a un repository ni escribe SQL.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.producto import ProductoCrear, ProductoOut, ProductoUpdate
from app.services import producto_service

router = APIRouter(prefix="/api/productos", tags=["Productos"])


@router.get("")
async def listar_productos(
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("pos:acceder")),
) -> Any:
    """Lista todos los productos activos (usado por caja y check-in)."""
    productos = await producto_service.listar_activos(conn)
    return [asdict(p) for p in productos]


@router.get("/admin", response_model=list[ProductoOut])
async def listar_productos_admin(
    sucursal_id: UUID | None = None,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:ver")),
) -> list[ProductoOut]:
    """Lista productos activos e inactivos, para la pantalla de catálogo."""
    return await producto_service.listar_todos(conn, sucursal_id)


@router.get("/{producto_id}", response_model=ProductoOut)
async def obtener_producto(
    producto_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:ver")),
) -> ProductoOut:
    return await producto_service.obtener(conn, producto_id)


@router.post("", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
async def crear_producto(
    body: ProductoCrear,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("inventario:gestionar_productos")),
) -> ProductoOut:
    usuario_id = UUID(current_user.sub) if current_user.sub else None
    return await producto_service.crear(conn, body, usuario_id=usuario_id)


@router.patch("/{producto_id}", response_model=ProductoOut)
async def actualizar_producto(
    producto_id: UUID,
    body: ProductoUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("inventario:gestionar_productos")),
) -> ProductoOut:
    usuario_id = UUID(current_user.sub) if current_user.sub else None
    return await producto_service.actualizar(conn, producto_id, body, usuario_id=usuario_id)

@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def eliminar_producto(
    producto_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("inventario:eliminar_producto")),
) -> None:
    usuario_id = UUID(current_user.sub) if current_user.sub else None
    await producto_service.eliminar(conn, producto_id, usuario_id=usuario_id)
