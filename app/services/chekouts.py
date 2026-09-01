from datetime import UTC, datetime
from math import ceil
from typing import Any
from uuid import UUID
from decimal import Decimal

import asyncpg
from fastapi import HTTPException

from app.core.ws_manager import manager
from app.repositories.caja_repository import registrar_movimiento_caja
from app.repositories.cargos_extra_estancia import make_extra_charge
from app.repositories.detalles_registro import (
    count_detalles_registro_abiertos,
    get_detalle_registro_by_id,
    put_hora_salida_by_id,
)
from app.repositories.pagos_comanda import pago_create
from app.repositories.registros import (
    EstadoRegistro,
    change_registro_estado,
    registro_add_total,
)
from app.repositories.productos import get_productos_estancia_by_sucursal_id, get_precio_pulsera_by_reserva_id
from app.repositories.producto_repository import get_producto_estancia_by_branch_id
from app.repositories.reservaciones_repository import get_reservacion_id_by_detalle_registro_id
from app.schemas.pagos import PagoIn


EXTRA_GRACE_MINUTES = 10

CENTAVO = 0.01


async def _calcular_cargo_extra(conn: asyncpg.Connection, detalle: dict[str, Any], now: datetime) -> tuple[int, float]:
    """Calcula horas extra y monto a cobrar por tiempo excedido, con la
    misma fórmula tanto para cotizar como para confirmar el checkout, así
    ninguna de las dos rutas se puede desincronizar de la otra."""
    salida_esperada = detalle["salida_esperada"]

    if salida_esperada is None:
        raise HTTPException(400, "Detalle sin salida esperada")

    minutos_extra = (now - salida_esperada).total_seconds() / 60

    extra_horas = 0
    if minutos_extra > EXTRA_GRACE_MINUTES:
        extra_horas = ceil((minutos_extra - EXTRA_GRACE_MINUTES) / 60)

    precio = detalle["precio"]
    total_extra = precio * extra_horas

    return extra_horas, total_extra


async def cotizar_checkout(conn: asyncpg.Connection, detalle_id: UUID) -> dict[str, Any]:
    """Calcula cuánto se debería cobrar por tiempo excedido en este instante,
    sin registrar nada (no pone hora_salida, no crea cargo)."""
    detalle = await get_detalle_registro_by_id(conn, detalle_id)

    if not detalle:
        raise HTTPException(404, "Detalle no encontrado")

    if detalle["salida"] is not None:
        raise HTTPException(400, "El niño ya realizó checkout")

    now = datetime.now(UTC)
    extra_horas, total_extra = await _calcular_cargo_extra(conn, detalle, now)

    return {
        "detalleId": str(detalle_id),
        "horasExtra": extra_horas,
        "totalExtra": float(total_extra),
        "cotizadoEn": now.isoformat(),
    }


async def create_chekout(
    conn: asyncpg.Connection,
    detalle_id: UUID,
    usuario_id: UUID,
    pagos: list[PagoIn],
    apertura_caja_id: str,
) -> dict[str, Any]:
    async with conn.transaction():
        now = datetime.now(UTC)

        detalle = await get_detalle_registro_by_id(conn, detalle_id)

        if not detalle:
            raise HTTPException(404, "Detalle no encontrado")

        if detalle["salida"] is not None:
            raise HTTPException(400, "El niño ya realizó checkout")

        # Recalculado con la hora real de este instante
        extra_horas, total_extra = await _calcular_cargo_extra(conn, detalle, now)

        if total_extra > 0:
            monto_pagado = sum(Decimal(str(pago.monto)) for pago in pagos)
            if abs(monto_pagado - total_extra) > CENTAVO:
                # El detail va estructurado para que el frontend pueda reintentar con el monto correcto
                raise HTTPException(
                    409,
                    detail={
                        "message": (
                            f"El monto a cobrar cambió: ahora se deben ${total_extra:.2f} "
                            f"({extra_horas}h extra)."
                        ),
                        "horasExtra": extra_horas,
                        "totalExtra": float(total_extra),
                    },
                )

        await put_hora_salida_by_id(conn, usuario_id, detalle_id)

        if extra_horas > 0:
            precio_unitario = total_extra / extra_horas
            await make_extra_charge(
                conn,
                detalle["sucursal_id"],
                detalle["registros_id"],
                detalle_id,
                extra_horas,
                precio_unitario,
                total_extra,
                usuario_id,
            )
            await registro_add_total(conn, total_extra, usuario_id, detalle["registros_id"])

            for pago in pagos:
                await pago_create(
                    conn,
                    detalle["sucursal_id"],
                    detalle["registros_id"],
                    pago.metodoPagoId,
                    pago.monto,
                    usuario_id,
                )
                await registrar_movimiento_caja(
                    conn,
                    apertura_caja_id=apertura_caja_id,
                    tipo_movimiento="E",
                    referencia_id=str(detalle["registros_id"]),
                    metodo_pago_id=str(pago.metodoPagoId),
                    monto=Decimal(str(pago.monto)),
                    creado_por=str(usuario_id),
                )

        abiertos = await count_detalles_registro_abiertos(conn, detalle["registros_id"])

        if abiertos == 0:
            await change_registro_estado(
                conn, EstadoRegistro.CERRADO, usuario_id, detalle["registros_id"]
            )

        resultado = {
            "detalleId": str(detalle_id),
            "registroId": str(detalle["registros_id"]),
            "horasExtra": extra_horas,
            "totalExtra": float(total_extra),
            "ninosRestantes": abiertos,
        }

    # Se notifica ya fuera de la transacción, para no avisar a los clientes
    # de datos que todavía podrían revertirse por un rollback.
    await manager.broadcast(
        str(detalle["sucursal_id"]),
        {
            "type": "estancia_checkout",
            "sucursalId": str(detalle["sucursal_id"]),
            "detalleId": str(detalle_id),
            "registroId": str(detalle["registros_id"]),
        },
    )

    return resultado
