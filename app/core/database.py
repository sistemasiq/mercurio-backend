from collections.abc import AsyncGenerator
from typing import Any

import asyncpg

from app.core.config import settings

_pool: asyncpg.Pool[asyncpg.Record] | None = None


async def create_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(settings.database_url)


async def close_pool() -> None:
    if _pool is not None:
        await _pool.close()


async def get_db() -> AsyncGenerator[asyncpg.Connection[Any], None]:
    if _pool is None:
        raise RuntimeError("El pool de base de datos no está inicializado")
    async with _pool.acquire() as conn:
        yield conn
