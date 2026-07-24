"""
app/api/routers/productos.py
Router de productos — solo delega al service.
SAD §3.2 / Regla 11.4: el router nunca accede a un repository ni escribe SQL.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from app.api.deps import get_current_user, require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.producto import ProductoCrear, ProductoOut, ProductoUpdate
from app.services import producto_service

router = APIRouter(prefix="/api/productos", tags=["Productos"])


@router.get("/catalogo")
async def listar_productos_cajero(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return await producto_service.obtener_productos_para_cajero(conn, current_user)


@router.get("/admin", response_model=list[ProductoOut])
async def listar_productos_admin(
    sucursal_id: UUID | None = None,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:ver")),
) -> list[ProductoOut]:
    """Lista productos activos e inactivos, para la pantalla de catálogo."""
    return await producto_service.listar_todos(conn, sucursal_id)


@router.get("/{producto_id}/combo-hijos")
async def obtener_combo_hijos(
    producto_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> Any:
    """Retorna los hijos de un combo para su expansión en el carrito."""
    return await producto_service.obtener_hijos_combo(conn, producto_id)


@router.get("/{producto_id}", response_model=ProductoOut)
async def obtener_producto(
    producto_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:ver")),
) -> ProductoOut:
    return await producto_service.obtener(conn, producto_id)


@router.post("", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
async def crear_producto(
    payload: str = Form(..., description="JSON string con los datos de ProductoCrear"),
    imagen: UploadFile | None = File(None),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("inventario:gestionar_productos")),
) -> ProductoOut:
    try:
        body = ProductoCrear.model_validate_json(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from e

    usuario_id = UUID(current_user.sub) if current_user.sub else None
    return await producto_service.crear(conn, body, usuario_id=usuario_id, imagen=imagen)


@router.patch("/{producto_id}", response_model=ProductoOut)
async def actualizar_producto(
    producto_id: UUID,
    payload: str = Form(..., description="JSON string con los datos de ProductoUpdate"),
    imagen: UploadFile | None = File(None),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("inventario:gestionar_productos")),
) -> ProductoOut:
    try:
        body = ProductoUpdate.model_validate_json(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from e

    usuario_id = UUID(current_user.sub) if current_user.sub else None
    return await producto_service.actualizar(
        conn, producto_id, body, usuario_id=usuario_id, imagen=imagen
    )


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def eliminar_producto(
    producto_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("inventario:eliminar_producto")),
) -> None:
    usuario_id = UUID(current_user.sub) if current_user.sub else None
    await producto_service.eliminar(conn, producto_id, usuario_id=usuario_id)
