from uuid import UUID

import asyncpg


async def validate_padres_token(
    conn: asyncpg.Connection, token: UUID
) -> dict[str, UUID] | None:
    """Retorna {tutor_id, sucursal_id} si el token es válido, None si no."""
    row = await conn.fetchrow(
        """
        SELECT t.id AS tutor_id, t.sucursal_id
        FROM public.tutores t
        WHERE t.token_acceso = $1
          AND t.activo = TRUE
        """,
        token,
    )
    return dict(row) if row else None
