from __future__ import annotations

from datetime import datetime
from typing import TypedDict
from uuid import UUID

import asyncpg

from app.core.roles import ROLES_SIN_SUCURSAL_FIJA


class UsuarioRecord(TypedDict):
    id: UUID
    email: str
    password_hash: str
    pin_hash: str | None
    nombre_completo: str
    apellidos: str | None
    telefono: str | None
    rol: str
    sucursal_id: UUID | None
    activo: bool
    ultimo_acceso: datetime | None


def _row_to_record(row: asyncpg.Record) -> UsuarioRecord:
    return UsuarioRecord(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        pin_hash=row["pin_hash"],
        nombre_completo=row["nombre_completo"],
        apellidos=row["apellidos"],
        telefono=row["telefono"],
        rol=row["rol"],
        sucursal_id=row["sucursal_id"],
        activo=row["activo"],
        ultimo_acceso=row["ultimo_acceso"],
    )


# AdministradorSistema no usa sucursal y Administrador se resuelve aparte
# (puede tener varias, ver get_sucursal_ids_activas); cualquier otro rol
# —incluidos los creados desde el Catálogo de Roles— opera en una sola
# sucursal fija a través de este join. Debe reflejar ROLES_SIN_SUCURSAL_FIJA.
_ROLES_EXCLUIDOS_SQL = ", ".join(f"'{rol}'" for rol in ROLES_SIN_SUCURSAL_FIJA)

_SELECT = f"""
    SELECT
        u.id,
        u.email,
        u.password_hash,
        u.pin_hash,
        u.nombre_completo,
        u.apellidos,
        u.telefono,
        r.nombre AS rol,
        us.sucursal_id,
        u.activo,
        u.ultimo_acceso
    FROM public.usuarios u
    JOIN public.roles r ON r.id = u.rol
    LEFT JOIN public.usuarios_sucursal us
           ON us.usuario_id = u.id AND us.activo = TRUE
           AND r.nombre NOT IN ({_ROLES_EXCLUIDOS_SQL})
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
    apellidos: str | None = None,
    telefono: str | None = None,
    pin_hash: str | None = None,
) -> UUID:
    row = await conn.fetchrow(
        """
        INSERT INTO public.usuarios
            (email, password_hash, nombre_completo, apellidos, telefono, rol, creado_por, pin_hash)
        VALUES ($1, $2, $3, $4, $5, (SELECT id FROM public.roles WHERE nombre = $6), $7, $8)
        RETURNING id
        """,
        email,
        password_hash,
        nombre_completo,
        apellidos,
        telefono,
        rol,
        creado_por,
        pin_hash,
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
    apellidos: str | None = None,
    telefono: str | None = None,
    activo: bool | None = None,
    pin_hash: str | None = None,
) -> bool:
    result = await conn.execute(
        """
        UPDATE public.usuarios
        SET email           = $1,
            nombre_completo = $2,
            apellidos       = $3,
            telefono        = $4,
            rol             = (SELECT id FROM public.roles WHERE nombre = $5),
            password_hash   = COALESCE($6, password_hash),
            activo          = COALESCE($7, activo),
            modificado      = NOW(),
            modificado_por  = $8,
            pin_hash        = COALESCE($10, pin_hash)
        WHERE id = $9 AND activo = TRUE
        """,
        email,
        nombre_completo,
        apellidos,
        telefono,
        rol,
        password_hash,
        activo,
        modificado_por,
        user_id,
        pin_hash,
    )
    return str(result) == "UPDATE 1"


async def update_ultimo_acceso(conn: asyncpg.Connection, user_id: UUID) -> None:
    """Registra el momento del login exitoso. Llamar desde auth_service.login."""
    await conn.execute(
        "UPDATE public.usuarios SET ultimo_acceso = NOW() WHERE id = $1",
        user_id,
    )


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
