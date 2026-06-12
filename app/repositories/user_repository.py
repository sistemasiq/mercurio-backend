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


def _row_to_record(row: asyncpg.Record) -> UsuarioRecord:
    return UsuarioRecord(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        nombre_completo=row["nombre_completo"],
        rol=row["rol"],
        sucursal_id=row["sucursal_id"],
        activo=row["activo"],
    )


_SELECT = """
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
"""


async def get_usuario_by_email(conn: asyncpg.Connection, email: str) -> UsuarioRecord | None:
    """Devuelve el usuario activo por email para el flujo de login."""
    row = await conn.fetchrow(
        _SELECT + "WHERE u.email = $1 AND u.activo = TRUE LIMIT 1",
        email,
    )
    return _row_to_record(row) if row else None


async def get_usuario_by_id(conn: asyncpg.Connection, user_id: UUID) -> UsuarioRecord | None:
    row = await conn.fetchrow(
        _SELECT + "WHERE u.id = $1 LIMIT 1",
        user_id,
    )
    return _row_to_record(row) if row else None


async def get_all_usuarios(conn: asyncpg.Connection) -> list[UsuarioRecord]:
    rows = await conn.fetch(_SELECT + "WHERE u.activo = TRUE ORDER BY u.creado DESC")
    return [_row_to_record(r) for r in rows]


async def get_usuarios_by_branch(conn: asyncpg.Connection, branch_id: UUID) -> list[UsuarioRecord]:
    rows = await conn.fetch(
        _SELECT + "WHERE us.sucursal_id = $1 AND u.activo = TRUE ORDER BY u.creado DESC",
        branch_id,
    )
    return [_row_to_record(r) for r in rows]


async def email_exists(conn: asyncpg.Connection, email: str) -> bool:
    row = await conn.fetchrow("SELECT id FROM public.usuarios WHERE email = $1", email)
    return row is not None


async def create_usuario(
    conn: asyncpg.Connection,
    email: str,
    password_hash: str,
    nombre_completo: str,
    rol: str,
    creado_por: UUID,
) -> UUID:
    row = await conn.fetchrow(
        """
        INSERT INTO public.usuarios
            (email, password_hash, nombre_completo, rol, creado_por)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """,
        email,
        password_hash,
        nombre_completo,
        rol,
        creado_por,
    )
    return UUID(str(row["id"]))


async def update_usuario(
    conn: asyncpg.Connection,
    user_id: UUID,
    email: str,
    nombre_completo: str,
    rol: str,
    password_hash: str | None,
    modificado_por: UUID,
) -> bool:
    result = await conn.execute(
        """
        UPDATE public.usuarios
        SET email          = $1,
            nombre_completo = $2,
            rol             = $3,
            password_hash   = COALESCE($4, password_hash),
            modificado      = NOW(),
            modificado_por  = $5
        WHERE id = $6 AND activo = TRUE
        """,
        email,
        nombre_completo,
        rol,
        password_hash,
        modificado_por,
        user_id,
    )
    return str(result) == "UPDATE 1"


async def update_usuario_branch(
    conn: asyncpg.Connection,
    usuario_id: UUID,
    sucursal_id: UUID | None,
    modificado_por: UUID,
) -> None:
    await conn.execute(
        """
        UPDATE public.usuarios_sucursal
        SET activo = FALSE, modificado = NOW(), modificado_por = $1
        WHERE usuario_id = $2 AND activo = TRUE
        """,
        modificado_por,
        usuario_id,
    )
    if sucursal_id is not None:
        await conn.execute(
            """
            INSERT INTO public.usuarios_sucursal (usuario_id, sucursal_id, creado_por)
            VALUES ($1, $2, $3)
            ON CONFLICT (usuario_id, sucursal_id)
            DO UPDATE SET activo = TRUE, modificado = NOW(), modificado_por = EXCLUDED.creado_por
            """,
            usuario_id,
            sucursal_id,
            modificado_por,
        )


async def delete_usuario(conn: asyncpg.Connection, user_id: UUID, modificado_por: UUID) -> bool:
    result = await conn.execute(
        """
        UPDATE public.usuarios
        SET activo = FALSE, modificado = NOW(), modificado_por = $1
        WHERE id = $2 AND activo = TRUE
        """,
        modificado_por,
        user_id,
    )
    return str(result) == "UPDATE 1"


async def assign_usuario_to_branch(
    conn: asyncpg.Connection,
    usuario_id: UUID,
    sucursal_id: UUID,
    creado_por: UUID,
) -> None:
    await conn.execute(
        """
        INSERT INTO public.usuarios_sucursal
            (usuario_id, sucursal_id, creado_por)
        VALUES ($1, $2, $3)
        """,
        usuario_id,
        sucursal_id,
        creado_por,
    )
