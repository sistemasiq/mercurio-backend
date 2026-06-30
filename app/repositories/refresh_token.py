from datetime import datetime
from uuid import UUID

import asyncpg


async def crear(
    conn: asyncpg.Connection,
    *,
    usuario_id: UUID,
    token_hash: str,
    expires_at: datetime,
) -> asyncpg.Record:
    return await conn.fetchrow(
        """
        INSERT INTO public.refresh_tokens (usuario_id, token_hash, expires_at)
        VALUES ($1, $2, $3)
        RETURNING *
        """,
        usuario_id,
        token_hash,
        expires_at,
    )


async def obtener_por_hash(conn: asyncpg.Connection, token_hash: str) -> asyncpg.Record | None:
    return await conn.fetchrow(
        "SELECT * FROM public.refresh_tokens WHERE token_hash = $1", token_hash
    )


async def revocar(conn: asyncpg.Connection, token_hash: str) -> None:
    await conn.execute(
        "UPDATE public.refresh_tokens SET revocado = TRUE WHERE token_hash = $1",
        token_hash,
    )


async def revocar_todos_de_usuario(conn: asyncpg.Connection, usuario_id: UUID) -> None:
    await conn.execute(
        "UPDATE public.refresh_tokens SET revocado = TRUE WHERE usuario_id = $1",
        usuario_id,
    )
