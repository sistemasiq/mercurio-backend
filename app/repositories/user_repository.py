from __future__ import annotations

from typing import TypedDict
from uuid import UUID

import asyncpg


class UsuarioRecord(TypedDict):
    id: UUID
    email: str
    password_hash: str
    nombre_completo: str
    rol: str
    sucursal_id: UUID | None
    activo: bool


async def get_usuario_by_email(conn: asyncpg.Connection, email: str) -> UsuarioRecord | None:
    """Devuelve el usuario activo con sus sucursales accesibles para el login."""
    row = await conn.fetchrow(
        """
        SELECT
            u.id,
            u.email,
            u.password_hash,
            u.nombre_completo,
            u.rol,
            us.sucursal_id,
            u.activo
        FROM public.usuarios u
        LEFT JOIN public.usuarios_sucursal us
               ON us.usuario_id = u.id AND us.activo = TRUE
        WHERE u.email = $1
          AND u.activo = TRUE
        LIMIT 1
        """,
        email,
    )
    if row is None:
        return None
    return UsuarioRecord(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        nombre_completo=row["nombre_completo"],
        rol=row["rol"],
        sucursal_id=row["sucursal_id"],
        activo=row["activo"],
    )
