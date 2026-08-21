from dataclasses import asdict
from typing import Any, Literal
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

import app.services.pago_service as svc
from app.api.deps import apertura_operando_id, require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.pagos import (
    DetalleOrdenOut,
    EstadisticasOut,
    HistorialOut,
    PagoCompletoRequest,
    PaymentOut,
    PaymentRequest,
)

router = APIRouter(prefix="/api/pagos", tags=["Pagos"])


def _get_active_branch(current_user: TokenData) -> UUID:
    if current_user.branch_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La sesión no tiene una sucursal activa.",
        )
    return current_user.branch_id


@router.post(
    "",
    response_model=list[PaymentOut],
    status_code=status.HTTP_201_CREATED,
    summary="Registrar pagos de una comanda",
    description=(
        "Recibe uno o más pagos asociados a una comanda, valida que "
        "el total coincida con el esperado y los persiste en pagos_ordenes."
    ),
)
async def registrar_pagos(
    body: PaymentRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("restaurante:registrar_pago")),
) -> list[PaymentOut]:
    usuario_id = UUID(current_user.sub)
    return await svc.procesar_pagos(conn, body, usuario_id)


@router.post(
    "/completar",
    status_code=status.HTTP_201_CREATED,
    summary="Crear comanda y registrar pagos en una transacción",
    description=(
        "Recibe los datos de la comanda y los pagos. Crea la comanda, "
        "registra los pagos y notifica a cocina en una única transacción. "
        "Si falla cualquiera de los dos, nada se persiste."
    ),
)
async def completar_pago(
    body: PagoCompletoRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("restaurante:registrar_pago")),
    apertura_id: str = Depends(apertura_operando_id),
) -> dict[str, Any]:
    usuario_id = UUID(current_user.sub)
    sucursal_id = _get_active_branch(current_user)
    comanda = await svc.completar_pago(conn, body, usuario_id, sucursal_id, apertura_id)
    return asdict(comanda)


@router.get(
    "/estadisticas",
    response_model=EstadisticasOut,
    summary="Estadísticas de ventas del periodo",
    description=(
        "Devuelve total de ventas, órdenes y ticket promedio " "para el filtro temporal indicado."
    ),
)
async def listar_estadisticas(
    filtro: str = Query("hoy", regex="^(hoy|semana|mes)$"),
    fecha_inicio: str | None = Query(None),
    fecha_fin: str | None = Query(None),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("restaurante:registrar_pago")),
) -> EstadisticasOut:
    sucursal_id = _get_active_branch(current_user)
    return await svc.obtener_estadisticas(conn, sucursal_id, filtro, fecha_inicio, fecha_fin)


@router.get(
    "/detalles/{tipo_origen}/{referencia_id}",
    response_model=DetalleOrdenOut,
    summary="Detalle completo de una transacción",
    description=(
        "Devuelve el detalle de una venta (comanda POS, estancia o "
        "reservación): productos, totales, métodos de pago y el usuario "
        "que creó el registro."
    ),
)
async def obtener_detalle(
    tipo_origen: Literal["comanda", "estancia", "reservacion"],
    referencia_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("restaurante:registrar_pago")),
) -> DetalleOrdenOut:
    resultado = await svc.obtener_detalle(conn, tipo_origen, referencia_id)
    if resultado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la venta con el ID proporcionado.",
        )
    return resultado


@router.get(
    "/historial",
    response_model=list[HistorialOut],
    summary="Historial de transacciones",
    description=(
        "Devuelve los pagos de la sucursal del usuario autenticado. "
        "Acepta filtro temporal (hoy/semana/mes) y filtro de estado "
        "(todos/pagado/cancelado)."
    ),
)
async def listar_historial(
    filtro: str = Query("hoy", regex="^(hoy|semana|mes)$"),
    estado: str = Query("todos", regex="^(todos|pagado|cancelado)$"),
    fecha_inicio: str | None = Query(None),
    fecha_fin: str | None = Query(None),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("restaurante:registrar_pago")),
) -> list[HistorialOut]:
    sucursal_id = _get_active_branch(current_user)
    return await svc.obtener_historial(conn, sucursal_id, filtro, estado, fecha_inicio, fecha_fin)
