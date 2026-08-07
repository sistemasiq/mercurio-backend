"""
app/services/comanda_evento_scheduler.py
Loop periódico que revisa reservaciones confirmadas cuyo evento está por
comenzar y manda a Cocina, como una comanda, los alimentos del paquete +
los productos ad-hoc agregados al reservar — para que estén listos antes de
que arranque el evento. No hay scheduler previo en este backend; este loop
es la infraestructura nueva (ver plan de la migración 033).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import asyncpg

from app.core.database import get_pool
from app.repositories import (
    paquetes_repository,
    reservacion_productos_repository,
    reservaciones_repository,
)
from app.repositories.user_repository import get_usuario_by_email
from app.schemas.auth import TokenData
from app.schemas.comanda import ComandaCreate, DetalleCreate
from app.services import comanda_service

logger = logging.getLogger("mercury.comanda_evento_scheduler")

SISTEMA_EMAIL = "sistema@mercury.internal"
MINUTOS_ANTICIPACION = 120  # mandar a cocina 2 horas antes de hora_inicio
INTERVALO_SEGUNDOS = 300  # revisar cada 5 minutos

_token_sistema: TokenData | None = None


async def _obtener_token_sistema(conn: asyncpg.Connection) -> TokenData:
    global _token_sistema
    if _token_sistema is not None:
        return _token_sistema
    usuario = await get_usuario_by_email(conn, SISTEMA_EMAIL)
    if usuario is None:
        raise RuntimeError(
            f"Usuario sistema '{SISTEMA_EMAIL}' no existe — falta aplicar la migración "
            "033_reservacion_productos_y_comanda_evento.sql"
        )
    _token_sistema = TokenData(
        sub=str(usuario["id"]),
        email=SISTEMA_EMAIL,
        role="AdministradorSistema",
        branch_id=None,
        permissions=[],
        jti=str(uuid4()),
        exp=datetime.max,
    )
    return _token_sistema


async def _armar_detalles(
    conn: asyncpg.Connection, reservacion: dict[str, Any]
) -> list[DetalleCreate]:
    items_paquete = await paquetes_repository.obtener_items_de_paquete(
        conn, reservacion["paquete_id"]
    )
    items_adhoc = await reservacion_productos_repository.listar_con_nombre_por_reservacion(
        conn, reservacion["id"]
    )

    detalles: list[DetalleCreate] = []
    for item in items_paquete:
        precio: Decimal = item["precio_unitario"]
        cantidad = int(item["cantidad"])
        detalles.append(
            DetalleCreate(
                id=str(item["producto_id"]),
                nombre=item["nombre"],
                cantidad=cantidad,
                precio_unitario=precio,
                subtotal=precio * cantidad,
                notas_especiales="Incluido en el paquete",
            )
        )
    for item in items_adhoc:
        precio = item["precio_unitario"]
        cantidad = int(item["cantidad"])
        detalles.append(
            DetalleCreate(
                id=str(item["producto_id"]),
                nombre=item["nombre"],
                cantidad=cantidad,
                precio_unitario=precio,
                subtotal=precio * cantidad,
                notas_especiales=item.get("notas"),
            )
        )
    return detalles


async def _procesar_reservacion(conn: asyncpg.Connection, reservacion: dict[str, Any]) -> None:
    reservacion_id: UUID = reservacion["id"]
    detalles = await _armar_detalles(conn, reservacion)

    if not detalles:
        await reservaciones_repository.marcar_comanda_enviada(conn, reservacion_id)
        return

    total = sum((d.subtotal for d in detalles), Decimal("0"))
    # ticket_numero es VARCHAR(10) en BD — "EVT" + 7 chars del id, sin guiones.
    ticket_numero = f"EVT{str(reservacion_id).replace('-', '')[:7].upper()}"
    comanda_in = ComandaCreate(
        notas_generales=(
            f"Evento: {reservacion['nombre_cliente']} — "
            f"{reservacion['fecha_evento']} {str(reservacion['hora_inicio'])[:5]}"
        ),
        detalles_comanda=detalles,
        ticket_numero=ticket_numero,
        total_final=total,
        sucursal_id=reservacion["sucursal_id"],
    )

    token_sistema = await _obtener_token_sistema(conn)
    comanda = await comanda_service.crear_comanda(conn, comanda_in, token_sistema)
    await conn.execute(
        "UPDATE public.comandas SET reservacion_id = $1 WHERE id = $2",
        reservacion_id,
        UUID(comanda.id),
    )
    await reservaciones_repository.marcar_comanda_enviada(conn, reservacion_id)
    logger.info("Comanda %s creada para reservación %s", comanda.ticket_numero, reservacion_id)


async def revisar_eventos_pendientes(conn: asyncpg.Connection) -> None:
    pendientes = await reservaciones_repository.listar_pendientes_de_comanda(
        conn, MINUTOS_ANTICIPACION
    )
    for reservacion in pendientes:
        try:
            await _procesar_reservacion(conn, reservacion)
        except Exception:
            logger.exception(
                "Error al mandar a cocina los alimentos de la reservación %s — se reintentará "
                "en el siguiente ciclo.",
                reservacion["id"],
            )


async def loop_comandas_eventos() -> None:
    while True:
        try:
            pool = get_pool()
            async with pool.acquire() as conn:
                await revisar_eventos_pendientes(conn)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Error inesperado en el loop de comandas de eventos.")
        await asyncio.sleep(INTERVALO_SEGUNDOS)
