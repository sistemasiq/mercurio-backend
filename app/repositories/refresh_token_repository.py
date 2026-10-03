from __future__ import annotations

from datetime import datetime
from uuid import UUID

import asyncpg


async def create_refresh_token(
    conn: asyncpg.Connection,
    usuario_id: UUID,
    token_hash: str,
    expires_at: datetime,
    sucursal_id: UUID | None = None,
) -> None:
    await conn.execute(
        """
        INSERT INTO public.refresh_tokens (usuario_id, token_hash, expires_at, sucursal_id)
        VALUES ($1, $2, $3, $4)
        """,
        usuario_id,
        token_hash,
        expires_at,
        sucursal_id,
    )


async def get_refresh_token(
    conn: asyncpg.Connection,
    token_hash: str,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id, usuario_id, expires_at, revocado, sucursal_id
        FROM public.refresh_tokens
        WHERE token_hash = $1
        """,
        token_hash,
    )


async def revoke_refresh_token(conn: asyncpg.Connection, token_hash: str) -> None:
    await conn.execute(
        "UPDATE public.refresh_tokens SET revocado = TRUE WHERE token_hash = $1",
        token_hash,
    )


async def revoke_all_user_refresh_tokens(conn: asyncpg.Connection, usuario_id: UUID) -> None:
    """Revoca todos los refresh tokens del usuario (logout global)."""
    await conn.execute(
        "UPDATE public.refresh_tokens SET revocado = TRUE WHERE usuario_id = $1",
        usuario_id,
    )


async def cleanup_expired_refresh_tokens(conn: asyncpg.Connection) -> None:
    await conn.execute("DELETE FROM public.refresh_tokens WHERE expires_at < NOW()")
