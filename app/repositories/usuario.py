from uuid import UUID

import asyncpg


async def obtener_por_email(conn: asyncpg.Connection, email: str) -> asyncpg.Record | None:
    """Usuario activo por email, con el nombre del rol resuelto (join a roles)."""
    return await conn.fetchrow(
        """
        SELECT u.*, r.nombre AS rol_nombre
        FROM public.usuarios u
        JOIN public.roles r ON r.id = u.rol
        WHERE u.email = $1 AND u.activo = TRUE
        """,
        email.lower(),
    )


async def obtener_por_id(conn: asyncpg.Connection, usuario_id: UUID) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT u.*, r.nombre AS rol_nombre
        FROM public.usuarios u
        JOIN public.roles r ON r.id = u.rol
        WHERE u.id = $1 AND u.activo = TRUE
        """,
        usuario_id,
    )


async def obtener_sucursal_id(conn: asyncpg.Connection, usuario_id: UUID) -> UUID | None:
    """Sucursal asignada al usuario (la primera activa) vía usuarios_sucursal."""
    return await conn.fetchval(
        """
        SELECT sucursal_id FROM public.usuarios_sucursal
        WHERE usuario_id = $1 AND activo = TRUE
        ORDER BY creado
        LIMIT 1
        """,
        usuario_id,
    )
