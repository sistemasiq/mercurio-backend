from __future__ import annotations

from datetime import datetime
from uuid import UUID

import asyncpg


async def revoke_token(conn: asyncpg.Connection, jti: str, expires_at: datetime) -> None:
    await conn.execute(
        """
        INSERT INTO public.tokens_revocados (jti, expires_at)
        VALUES ($1, $2)
        ON CONFLICT (jti) DO NOTHING
        """,
        UUID(jti),
        expires_at,
    )


async def is_token_revoked(conn: asyncpg.Connection, jti: str) -> bool:
    row = await conn.fetchrow(
        "SELECT 1 FROM public.tokens_revocados WHERE jti = $1",
        UUID(jti),
    )
    return row is not None


async def cleanup_expired_tokens(conn: asyncpg.Connection) -> None:
    """Elimina entradas de tokens cuya expiración ya pasó. Llamar periódicamente."""
    await conn.execute("DELETE FROM public.tokens_revocados WHERE expires_at < NOW()")
