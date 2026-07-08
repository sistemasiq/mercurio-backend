from typing import Any
from uuid import UUID

import asyncpg

from app.repositories.pulseras import get_pulseras_disponibles_por_sucursal


async def get_pulseras_disponibles_by_sucursal_id(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> list[dict[str, Any]]:
    return await get_pulseras_disponibles_por_sucursal(conn, sucursal_id)
