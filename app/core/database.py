from collections.abc import AsyncGenerator

import asyncpg

from app.core.config import settings

_pool: asyncpg.Pool | None = None


async def create_pool() -> None:
    """Inicializa el pool global de asyncpg (llamado en el lifespan)."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=settings.asyncpg_dsn)


async def close_pool() -> None:
    """Cierra el pool global de asyncpg (llamado al apagar la app)."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Devuelve el pool ya inicializado o falla si el lifespan no corrió."""
    if _pool is None:
        raise RuntimeError("El pool de conexiones no está inicializado.")
    return _pool


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """Dependencia FastAPI: cede una conexión del pool por request."""
    async with get_pool().acquire() as conn:
        yield conn
