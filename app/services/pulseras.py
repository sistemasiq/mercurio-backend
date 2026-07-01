from typing import Any
from uuid import UUID

import asyncpg

from app.repositories.pulseras import get_pulseras_by_sucursal


async def get_pulseras_by_sucursal_id(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> list[dict[str, Any]]:
    return await get_pulseras_by_sucursal(conn, sucursal_id)
