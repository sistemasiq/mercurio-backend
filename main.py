import app.models  # noqa: F401 — registra todos los modelos SQLAlchemy al arrancar

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes.auth import router as auth_router
from app.routes.sucursal import router as sucursal_router
from app.routes.tipos_evento import router as tipos_evento_router
from app.routes.metodos_pago import router as metodos_pago_router
from app.routes.extras import router as extras_router
from app.routes.paquetes import router as paquetes_router
from app.routes.paquete_tipos_evento import router as paquete_tipos_evento_router
from app.routes.reservaciones import router as reservaciones_router
from app.routes.reservacion_extras import router as reservacion_extras_router
from app.routes.pagos_reservacion import router as pagos_reservacion_router

app = FastAPI(title=settings.APP_TITLE, version=settings.APP_VERSION)

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
