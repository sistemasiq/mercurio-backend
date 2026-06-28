import asyncpg
from uuid import UUID

from app.repositories.pulseras import get_pulseras_by_sucursal

async def get_pulseras_by_sucursal_id(conn: asyncpg.Connection,sucursal_id: UUID,):
    return get_pulseras_by_sucursal(conn,sucursal_id)