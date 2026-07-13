import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import RequestResponseEndpoint

from app.api.routers import (
    auth,
    branches,
    comandas,
    documentos,
    estancias,
    extras,
    metodos_pago,
    pagos,
    pagos_reservacion,
    paquete_tipos_evento,
    paquetes,
    permissions,
    productos,
    pulseras,
    reservacion_extras,
    reservaciones,
    tipos_evento,
    users,
)
from app.core.config import settings
from app.core.database import close_pool, create_pool, get_pool

logger = logging.getLogger("mercury.debug")
logging.basicConfig(level=logging.INFO)


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
async def log_requests(request: Request, call_next: RequestResponseEndpoint) -> Response:
    body = await request.body()
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        body_str = "<multipart form-data with files>"
    else:
        try:
            body_str = body.decode("utf-8")
        except UnicodeDecodeError:
            body_str = "<binary data unreadable>"

    # logger.debug(">>> %s %s | body: %s", request.method, request.url.path, body_str)
    response = await call_next(request)
    return response


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(branches.router)
app.include_router(permissions.router)
app.include_router(comandas.router)
app.include_router(productos.router)
app.include_router(extras.router)
app.include_router(metodos_pago.router)
app.include_router(pagos.router)
app.include_router(pagos_reservacion.router)
app.include_router(paquetes.router)
app.include_router(paquete_tipos_evento.router)
app.include_router(reservaciones.router)
app.include_router(reservacion_extras.router)
app.include_router(tipos_evento.router)
app.include_router(estancias.router)
app.include_router(pulseras.router)
app.include_router(documentos.router)
