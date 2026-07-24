"""
app/api/routers/proveedores.py
Router de proveedores — solo delega al service.
SAD §3.2 / Regla 11.4: el router nunca accede a un repository ni escribe SQL.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.proveedor import ProveedorCrear, ProveedorOut, ProveedorUpdate
from app.services import proveedor_service

router = APIRouter(prefix="/api/proveedores", tags=["Proveedores"])


@router.get("", response_model=list[ProveedorOut])
async def listar_proveedores(
    sucursal_id: UUID | None = None,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:ver")),
) -> list[ProveedorOut]:
    """Lista proveedores activos e inactivos, para la pantalla de catálogo."""
    return await proveedor_service.listar(conn, sucursal_id)


@router.get("/{proveedor_id}", response_model=ProveedorOut)
async def obtener_proveedor(
    proveedor_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:ver")),
) -> ProveedorOut:
    return await proveedor_service.obtener(conn, proveedor_id)


@router.post("", response_model=ProveedorOut, status_code=status.HTTP_201_CREATED)
async def crear_proveedor(
    body: ProveedorCrear,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("inventario:gestionar_proveedores")),
) -> ProveedorOut:
    return await proveedor_service.crear(conn, body, current_user)


@router.patch("/{proveedor_id}", response_model=ProveedorOut)
async def actualizar_proveedor(
    proveedor_id: UUID,
    body: ProveedorUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("inventario:gestionar_proveedores")),
) -> ProveedorOut:
    return await proveedor_service.actualizar(conn, proveedor_id, body, current_user)


@router.delete("/{proveedor_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def eliminar_proveedor(
    proveedor_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:eliminar_proveedor")),
) -> None:
    await proveedor_service.eliminar(conn, proveedor_id)
