from datetime import date
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Query

import app.services.lealtad_service as svc
from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.lealtad import (
    CELULAR_PATTERN,
    ConfiguracionLealtadBase,
    ConfiguracionLealtadOut,
    MovimientoPuntoOut,
    SaldoPuntosOut,
)

router = APIRouter(prefix="/api/lealtad", tags=["Lealtad"])


@router.get("/configuracion", response_model=ConfiguracionLealtadOut)
async def obtener_configuracion(
    sucursal_id: UUID | None = Query(None),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("lealtad:gestionar_configuracion")),
) -> ConfiguracionLealtadOut:
    return await svc.obtener_configuracion(conn, current_user, sucursal_id)


@router.put("/configuracion", response_model=ConfiguracionLealtadOut)
async def actualizar_configuracion(
    body: ConfiguracionLealtadBase,
    sucursal_id: UUID | None = Query(None),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("lealtad:gestionar_configuracion")),
) -> ConfiguracionLealtadOut:
    return await svc.actualizar_configuracion(conn, current_user, sucursal_id, body)


@router.get("/saldo", response_model=SaldoPuntosOut)
async def consultar_saldo(
    celular: str = Query(..., pattern=CELULAR_PATTERN),
    sucursal_id: UUID | None = Query(None),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("lealtad:ver_saldo")),
) -> SaldoPuntosOut:
    return await svc.consultar_saldo(conn, current_user, sucursal_id, celular)


@router.get("/movimientos", response_model=list[MovimientoPuntoOut])
async def listar_movimientos(
    celular: str = Query(..., pattern=CELULAR_PATTERN),
    sucursal_id: UUID | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("lealtad:ver_saldo")),
) -> list[MovimientoPuntoOut]:
    return await svc.listar_movimientos(conn, current_user, sucursal_id, celular, desde, hasta)
