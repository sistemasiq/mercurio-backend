"""
app/services/proveedor_service.py
Lógica de negocio para proveedores.
SAD §3.2: el service orquesta repositorios, nunca escribe SQL directamente.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado
from app.repositories import proveedor_repository
from app.schemas.auth import TokenData
from app.schemas.proveedor import ProveedorCrear, ProveedorOut, ProveedorUpdate


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[ProveedorOut]:
    rows = await proveedor_repository.listar(conn, sucursal_id)
    return [ProveedorOut.model_validate(r) for r in rows]


async def obtener(conn: asyncpg.Connection, proveedor_id: UUID) -> ProveedorOut:
    row = await proveedor_repository.obtener(conn, proveedor_id)
    if not row:
        raise NoEncontrado("Proveedor")
    return ProveedorOut.model_validate(row)


async def crear(
    conn: asyncpg.Connection, body: ProveedorCrear, current_user: TokenData
) -> ProveedorOut:
    row = await proveedor_repository.crear(
        conn,
        sucursal_id=body.sucursal_id,
        nombre=body.nombre,
        contacto_nombre=body.contacto_nombre,
        telefono=body.telefono,
        email=body.email,
        notas=body.notas,
        creado_por=UUID(current_user.sub),
    )
    return ProveedorOut.model_validate(row)


async def actualizar(
    conn: asyncpg.Connection,
    proveedor_id: UUID,
    body: ProveedorUpdate,
    current_user: TokenData,
) -> ProveedorOut:
    await obtener(conn, proveedor_id)
    updates = body.model_dump(exclude_unset=True)
    updates["modificado_por"] = UUID(current_user.sub)
    row = await proveedor_repository.actualizar(conn, proveedor_id, updates)
    if not row:
        raise NoEncontrado("Proveedor")
    return ProveedorOut.model_validate(row)


async def eliminar(conn: asyncpg.Connection, proveedor_id: UUID) -> None:
    await obtener(conn, proveedor_id)
    await proveedor_repository.eliminar(conn, proveedor_id)
