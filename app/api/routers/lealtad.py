from datetime import date
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

import app.services.lealtad_service as svc
from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.lealtad import (
    CELULAR_PATTERN,
    AjustePuntosRequest,
    ClienteLealtadOut,
    ConfiguracionLealtadBase,
    ConfiguracionLealtadOut,
    MovimientoPuntoOut,
    ReporteLealtadOut,
    SaldoPuntosOut,
)
from app.utils.csv_export import csv_streaming_response

router = APIRouter(prefix="/api/lealtad", tags=["Lealtad"])

_REPORTE_CSV_CAMPOS = ("celular", "nombre", "puntos_otorgados")


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


@router.get("/reporte", response_model=ReporteLealtadOut)
async def obtener_reporte(
    sucursal_id: UUID | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("lealtad:ver_reporte")),
) -> ReporteLealtadOut:
    return await svc.obtener_reporte(conn, current_user, sucursal_id, desde, hasta)


@router.get("/reporte/export", summary="Exporta el top de clientes del reporte de lealtad a CSV")
async def exportar_reporte(
    sucursal_id: UUID | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("lealtad:ver_reporte")),
) -> StreamingResponse:
    """Mismos filtros que `/lealtad/reporte`; entrega el top de clientes
    como descarga CSV (patrón de B7)."""
    reporte = await svc.obtener_reporte(conn, current_user, sucursal_id, desde, hasta)
    filas = (c.model_dump() for c in reporte.top_clientes)
    return csv_streaming_response(_REPORTE_CSV_CAMPOS, filas, "reporte_lealtad.csv")


@router.get("/clientes", response_model=list[ClienteLealtadOut])
async def buscar_clientes(
    q: str = Query(..., min_length=1),
    sucursal_id: UUID | None = Query(None),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("lealtad:ver_saldo")),
) -> list[ClienteLealtadOut]:
    return await svc.buscar_clientes(conn, current_user, sucursal_id, q)


@router.post("/ajustes", response_model=MovimientoPuntoOut)
async def ajustar_puntos(
    body: AjustePuntosRequest,
    sucursal_id: UUID | None = Query(None),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("lealtad:ajustar")),
) -> MovimientoPuntoOut:
    return await svc.ajustar_puntos(
        conn, current_user, sucursal_id, body.celular, body.puntos, body.motivo
    )
