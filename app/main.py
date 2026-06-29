import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import auth, branches, comandas, permissions, productos, users
from app.core.config import settings
from app.core.database import close_pool, create_pool, get_pool

logger = logging.getLogger("mercury.debug")
logging.basicConfig(level=logging.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await create_pool()
    async with get_pool().acquire() as conn:
        from app.services.permission_service import load_cache

        await load_cache(conn)
    yield
    await close_pool()


app = FastAPI(title="Mercury API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):  # type: ignore[no-untyped-def]
    body = await request.body()
    logger.debug(">>> %s %s | body: %s", request.method, request.url.path, body.decode())
    response = await call_next(request)
    logger.debug("<<< %s", response.status_code)
    return response


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(branches.router)
app.include_router(permissions.router)
# TODO: comandas y productos usan SQLAlchemy — deben migrarse a asyncpg antes de producción
app.include_router(comandas.router, prefix="/comandas", tags=["comandas"])
app.include_router(productos.router, prefix="/productos", tags=["productos"])
