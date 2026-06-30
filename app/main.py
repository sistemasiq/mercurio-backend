from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.auth import router as auth_router
from app.api.routers.eventos import router as eventos_router
from app.api.routers.extras import router as extras_router
from app.api.routers.metodos_pago import router as metodos_pago_router
from app.api.routers.pagos_reservacion import router as pagos_reservacion_router
from app.api.routers.paquete_tipos_evento import router as paquete_tipos_evento_router
from app.api.routers.paquetes import router as paquetes_router
from app.api.routers.reservacion_extras import router as reservacion_extras_router
from app.api.routers.reservaciones import router as reservaciones_router
from app.api.routers.sucursal import router as sucursal_router
from app.api.routers.tipos_evento import router as tipos_evento_router
from app.core.config import settings
from app.core.database import close_pool, create_pool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await create_pool()
    yield
    await close_pool()


app = FastAPI(title=settings.APP_TITLE, version=settings.APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(sucursal_router)
app.include_router(tipos_evento_router)
app.include_router(metodos_pago_router)
app.include_router(extras_router)
app.include_router(paquetes_router)
app.include_router(paquete_tipos_evento_router)
app.include_router(reservaciones_router)
app.include_router(reservacion_extras_router)
app.include_router(pagos_reservacion_router)
app.include_router(eventos_router)
