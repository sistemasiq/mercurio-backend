from datetime import datetime
from uuid import UUID

import asyncpg


async def agregar(conn: asyncpg.Connection, *, jti: UUID, expires_at: datetime) -> None:
    await conn.execute(
        """
        INSERT INTO public.tokens_revocados (jti, expires_at)
        VALUES ($1, $2)
        ON CONFLICT (jti) DO NOTHING
        """,
        jti,
        expires_at,
    )


async def esta_revocado(conn: asyncpg.Connection, jti: UUID) -> bool:
    row = await conn.fetchrow("SELECT 1 FROM public.tokens_revocados WHERE jti = $1", jti)
    return row is not None
