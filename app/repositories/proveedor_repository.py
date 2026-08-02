"""
app/repositories/proveedor_repository.py
Única capa que habla con la BD para proveedores — SQL crudo con asyncpg.
Regla 11.1 y 11.4 SAD.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import asyncpg

_COLUMNS = """
    id, sucursal_id, nombre, contacto_nombre, telefono, email, notas,
    activo, creado, creado_por, modificado, modificado_por
"""


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[dict[str, Any]]:
    """Lista proveedores (activos e inactivos), para la pantalla de administración.
    Sin sucursal_id devuelve de todas las sucursales (uso de AdministradorSistema)."""
    if sucursal_id:
        rows = await conn.fetch(
            f"SELECT {_COLUMNS} FROM public.proveedores WHERE sucursal_id = $1 ORDER BY nombre ASC",
            sucursal_id,
        )
    else:
        rows = await conn.fetch(f"SELECT {_COLUMNS} FROM public.proveedores ORDER BY nombre ASC")
    return [dict(r) for r in rows]


async def obtener(conn: asyncpg.Connection, proveedor_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(
        f"SELECT {_COLUMNS} FROM public.proveedores WHERE id = $1", proveedor_id
    )
    return dict(row) if row else None


async def crear(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    nombre: str,
    contacto_nombre: str | None,
    telefono: str | None,
    email: str | None,
    notas: str | None,
    creado_por: UUID,
) -> dict[str, Any]:
    row = await conn.fetchrow(
        f"""
        INSERT INTO public.proveedores
            (sucursal_id, nombre, contacto_nombre, telefono, email, notas, creado_por)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING {_COLUMNS}
        """,
        sucursal_id,
        nombre,
        contacto_nombre,
        telefono,
        email,
        notas,
        creado_por,
    )
    return dict(row)


async def actualizar(
    conn: asyncpg.Connection, proveedor_id: UUID, updates: dict[str, Any]
) -> dict[str, Any] | None:
    if not updates:
        return await obtener(conn, proveedor_id)
    set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
    set_parts.append("modificado = NOW()")
    sql = (
        f"UPDATE public.proveedores SET {', '.join(set_parts)} WHERE id = $1 "
        f"RETURNING {_COLUMNS}"
    )
    row = await conn.fetchrow(sql, proveedor_id, *updates.values())
    return dict(row) if row else None


async def eliminar(conn: asyncpg.Connection, proveedor_id: UUID) -> bool:
    result = await conn.execute(
        "UPDATE public.proveedores SET activo = FALSE, modificado = NOW() "
        "WHERE id = $1 AND activo = TRUE",
        proveedor_id,
    )
    return bool(result == "UPDATE 1")
