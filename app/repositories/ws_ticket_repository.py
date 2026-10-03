from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import asyncpg


async def create_ws_ticket(
    conn: asyncpg.Connection,
    ticket_hash: str,
    claims: dict[str, Any],
    expires_at: datetime,
) -> None:
    await conn.execute(
        """
        INSERT INTO public.ws_tickets (ticket_hash, claims, expires_at)
        VALUES ($1, $2::jsonb, $3)
        """,
        ticket_hash,
        json.dumps(claims),
        expires_at,
    )


async def consume_ws_ticket(
    conn: asyncpg.Connection,
    ticket_hash: str,
) -> dict[str, Any] | None:
    """Marca el ticket como usado de forma atómica y devuelve sus claims, o
    None si no existe, ya se usó o expiró (de un solo uso, QA #32)."""
    row = await conn.fetchrow(
        """
        UPDATE public.ws_tickets
        SET usado = TRUE
        WHERE ticket_hash = $1 AND usado = FALSE AND expires_at > NOW()
        RETURNING claims
        """,
        ticket_hash,
    )
    if row is None:
        return None
    claims = row["claims"]
    return json.loads(claims) if isinstance(claims, str) else dict(claims)


async def cleanup_expired_ws_tickets(conn: asyncpg.Connection) -> None:
    """Elimina tickets ya expirados. Llamar periódicamente."""
    await conn.execute("DELETE FROM public.ws_tickets WHERE expires_at < NOW()")
