"""
app/api/routers/insumos.py
Router de insumos — solo delega al service.
SAD §3.2 / Regla 11.4: el router nunca accede a un repository ni escribe SQL.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.insumo import (
    InsumoAlertasOut,
    InsumoCrear,
    InsumoOut,
    InsumoRecetaInversaOut,
    InsumoUpdate,
)
from app.schemas.movimiento_inventario import CogsRenglonOut, ResumenCogsOut
from app.services import insumo_service, inventario_service
from app.utils.csv_export import csv_streaming_response

router = APIRouter(prefix="/api/insumos", tags=["Insumos"])

_STOCK_CSV_CAMPOS = [
    "id",
    "nombre",
    "stock_actual",
    "stock_minimo",
    "punto_reorden",
    "stock_maximo",
    "costo_unitario",
    "proveedor_principal_id",
    "activo",
]

_COGS_CSV_CAMPOS = ["insumo_id", "insumo_nombre", "cantidad_salida", "costo_total"]


@router.get("", response_model=list[InsumoOut])
async def listar_insumos(
    sucursal_id: UUID | None = None,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:ver")),
) -> list[InsumoOut]:
    """Lista insumos activos e inactivos, para la pantalla de catálogo."""
    return await insumo_service.listar(conn, sucursal_id)


@router.get("/alertas", response_model=InsumoAlertasOut)
async def listar_alertas(
    sucursal_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:ver")),
) -> InsumoAlertasOut:
    """Insumos de la sucursal por debajo de su punto de reorden, separados en
    críticos (< mínimo) y por-reordenar. Para el badge de alerta del menú."""
    return await insumo_service.listar_alertas(conn, sucursal_id)


@router.get("/reporte-cogs", response_model=list[CogsRenglonOut])
async def reporte_cogs(
    sucursal_id: UUID,
    desde: date | None = None,
    hasta: date | None = None,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("reportes:inventario")),
) -> list[CogsRenglonOut]:
    """Costo de ventas (COGS): costo de lo consumido por insumo en el periodo."""
    return await inventario_service.listar_cogs(conn, sucursal_id, desde, hasta)


@router.get("/reporte-cogs/resumen", response_model=ResumenCogsOut)
async def resumen_cogs(
    sucursal_id: UUID,
    desde: date | None = None,
    hasta: date | None = None,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("reportes:inventario")),
) -> ResumenCogsOut:
    """KPIs del periodo: ventas totales, costo de ventas, margen y merma."""
    return await inventario_service.resumen_cogs(conn, sucursal_id, desde, hasta)


@router.get("/export", summary="Exporta el reporte de stock a CSV")
async def exportar_stock(
    sucursal_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("reportes:inventario")),
) -> StreamingResponse:
    """Reporte de stock (igual que `listar_insumos`) como descarga CSV."""
    insumos = await insumo_service.listar(conn, sucursal_id)
    filas = (i.model_dump() for i in insumos)
    return csv_streaming_response(_STOCK_CSV_CAMPOS, filas, "reporte_stock.csv")


@router.get("/reporte-cogs/export", summary="Exporta el costo de ventas (COGS) a CSV")
async def exportar_cogs(
    sucursal_id: UUID,
    desde: date | None = None,
    hasta: date | None = None,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("reportes:inventario")),
) -> StreamingResponse:
    renglones = await inventario_service.listar_cogs(conn, sucursal_id, desde, hasta)
    filas = (r.model_dump() for r in renglones)
    return csv_streaming_response(_COGS_CSV_CAMPOS, filas, "costo_de_ventas.csv")


@router.get("/estimaciones", response_model=list[InsumoRecetaInversaOut])
async def listar_estimaciones(
    sucursal_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:ver")),
) -> list[InsumoRecetaInversaOut]:
    """Receta inversa por insumo (qué productos A/B lo consumen y en qué cantidad).
    El FrontEnd calcula 'rinde para N unidades' con stock_actual / cantidad."""
    return await insumo_service.listar_estimaciones(conn, sucursal_id)


@router.get("/{insumo_id}", response_model=InsumoOut)
async def obtener_insumo(
    insumo_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:ver")),
) -> InsumoOut:
    return await insumo_service.obtener(conn, insumo_id)


@router.post("", response_model=InsumoOut, status_code=status.HTTP_201_CREATED)
async def crear_insumo(
    body: InsumoCrear,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("inventario:gestionar_insumos")),
) -> InsumoOut:
    return await insumo_service.crear(conn, body, current_user)


@router.patch("/{insumo_id}", response_model=InsumoOut)
async def actualizar_insumo(
    insumo_id: UUID,
    body: InsumoUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("inventario:gestionar_insumos")),
) -> InsumoOut:
    return await insumo_service.actualizar(conn, insumo_id, body, current_user)


@router.delete("/{insumo_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def eliminar_insumo(
    insumo_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:eliminar_insumo")),
) -> None:
    await insumo_service.eliminar(conn, insumo_id)
