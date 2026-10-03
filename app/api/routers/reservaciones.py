from datetime import date
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Query, status

import app.services.disponibilidad as disponibilidad_svc
import app.services.reservaciones as svc
from app.api.deps import apertura_operando_id, require_permission
from app.core.database import get_db
from app.core.scope import sucursal_scope
from app.schemas.auth import TokenData
from app.schemas.disponibilidad import DisponibilidadResponse
from app.schemas.reservaciones import (
    EventoDelDiaOut,
    ReservacionesCrear,
    ReservacionesOut,
    ReservacionesUpdate,
)
from app.schemas.reservaciones_completa import (
    ReservacionCompletaRequest,
    ReservacionCompletaResponse,
)

router = APIRouter(prefix="/api/reservaciones", tags=["Reservaciones"])


@router.get("", response_model=list[ReservacionesOut])
async def listar_reservaciones(
    desde: date | None = Query(None, description="Filtra por fecha_evento >= desde"),
    hasta: date | None = Query(None, description="Filtra por fecha_evento <= hasta"),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("reservaciones:listar")),
) -> list[ReservacionesOut]:
    return await svc.listar(conn, sucursal_scope(current_user), desde, hasta)


@router.get("/disponibilidad", response_model=DisponibilidadResponse)
async def obtener_disponibilidad(
    sucursal_id: UUID,
    fecha: date,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("reservaciones:ver")),
) -> DisponibilidadResponse:
    return await disponibilidad_svc.obtener_disponibilidad(conn, sucursal_id, fecha)


@router.get("/evento-cercano/{sucursal_id}", response_model=EventoDelDiaOut | None)
async def obtener_evento_cercano(
    sucursal_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("reservaciones:ver")),
) -> EventoDelDiaOut:
    return await svc.obtener_evento_cercano(conn, sucursal_id)


@router.get("/{reservacion_id}", response_model=ReservacionesOut)
async def obtener_reservacion(
    reservacion_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("reservaciones:ver")),
) -> ReservacionesOut:
    return await svc.obtener(conn, reservacion_id)


@router.post("", response_model=ReservacionesOut, status_code=status.HTTP_201_CREATED)
async def crear_reservacion(
    body: ReservacionesCrear,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("reservaciones:crear")),
) -> ReservacionesOut:
    return await svc.crear(conn, body, current_user.sub)


@router.post(
    "/completa",
    response_model=ReservacionCompletaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Alta atómica de una reservación (QA #10)",
    description=(
        "Crea la reservación junto con sus extras, productos y pagos (anticipo) "
        "en una única transacción: si algo falla, nada se persiste. Sustituye "
        "al loop de requests sueltos que hacía NuevaReservacionPage.vue."
    ),
)
async def crear_reservacion_completa(
    body: ReservacionCompletaRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("reservaciones:crear")),
    apertura_id: str = Depends(apertura_operando_id),
) -> ReservacionCompletaResponse:
    from app.services import turnos_caja_service

    disponible_antes = await turnos_caja_service.efectivo_disponible_actual(conn, apertura_id)
    resultado = await svc.crear_completa(conn, body, UUID(current_user.sub), apertura_id)
    if body.pagos:
        resultado.advertencia_efectivo = turnos_caja_service.advertencia_efectivo_insuficiente(
            disponible_antes, body.cambio
        )
    return resultado


@router.patch("/{reservacion_id}", response_model=ReservacionesOut)
async def actualizar_reservacion(
    reservacion_id: UUID,
    body: ReservacionesUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("reservaciones:editar")),
) -> ReservacionesOut:
    return await svc.actualizar(conn, reservacion_id, body)


@router.delete("/{reservacion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_reservacion(
    reservacion_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("reservaciones:eliminar")),
) -> None:
    await svc.eliminar(conn, reservacion_id)
