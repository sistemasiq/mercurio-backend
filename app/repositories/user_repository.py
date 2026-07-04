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
        r.nombre AS rol,
        us.sucursal_id,
        u.activo
    FROM public.usuarios u
    JOIN public.roles r ON r.id = u.rol
    LEFT JOIN public.usuarios_sucursal us
           ON us.usuario_id = u.id AND us.activo = TRUE
           AND r.nombre IN ('Cajero', 'Cocina')
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
        VALUES ($1, $2, $3, (SELECT id FROM public.roles WHERE nombre = $4), $5)
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
        SET email           = $1,
            nombre_completo = $2,
            rol             = (SELECT id FROM public.roles WHERE nombre = $3),
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


async def get_sucursal_ids_activas(conn: asyncpg.Connection, usuario_id: UUID) -> list[UUID]:
    """Sucursales activas de un usuario, sin asumir una sola (a diferencia de _SELECT).

    Agnóstica al rol: la usa el login para resolver cuántas/cuáles sucursales
    tiene un Administrador con potencialmente varias asignaciones.
    """
    rows = await conn.fetch(
        """
        SELECT sucursal_id FROM public.usuarios_sucursal
        WHERE usuario_id = $1 AND activo = TRUE
        ORDER BY sucursal_id
        """,
        usuario_id,
    )
    return [r["sucursal_id"] for r in rows]


async def assign_usuario_a_sucursal_especifica(
    conn: asyncpg.Connection,
    usuario_id: UUID,
    sucursal_id: UUID,
    creado_por: UUID,
) -> None:
    """Asigna un usuario a UNA sucursal específica sin tocar sus otras asignaciones.

    A diferencia de update_usuario_branch (que desactiva todas las filas
    activas del usuario antes de insertar), esta función habilita que un
    mismo Administrador quede asignado a varias sucursales a la vez.
    """
    await conn.execute(
        """
        INSERT INTO public.usuarios_sucursal (usuario_id, sucursal_id, creado_por)
        VALUES ($1, $2, $3)
        ON CONFLICT (usuario_id, sucursal_id)
        DO UPDATE SET activo = TRUE, modificado = NOW(), modificado_por = EXCLUDED.creado_por
        """,
        usuario_id,
        sucursal_id,
        creado_por,
    )


async def desasignar_usuario_de_sucursal(
    conn: asyncpg.Connection,
    usuario_id: UUID,
    sucursal_id: UUID,
    modificado_por: UUID,
) -> None:
    """Desactiva el vínculo de un usuario con UNA sucursal específica.

    Solo afecta ese par (usuario, sucursal); las demás asignaciones del
    mismo usuario a otras sucursales quedan intactas.
    """
    await conn.execute(
        """
        UPDATE public.usuarios_sucursal
        SET activo = FALSE, modificado = NOW(), modificado_por = $1
        WHERE usuario_id = $2 AND sucursal_id = $3 AND activo = TRUE
        """,
        modificado_por,
        usuario_id,
        sucursal_id,
    )


async def get_usuario_administrador_by_id(
    conn: asyncpg.Connection, usuario_id: UUID
) -> UUID | None:
    """Devuelve el id si el usuario existe, está activo y tiene rol Administrador."""
    row = await conn.fetchrow(
        """
        SELECT u.id
        FROM public.usuarios u
        JOIN public.roles r ON r.id = u.rol
        WHERE u.id = $1 AND u.activo = TRUE AND r.nombre = 'Administrador'
        """,
        usuario_id,
    )
    return UUID(str(row["id"])) if row else None
