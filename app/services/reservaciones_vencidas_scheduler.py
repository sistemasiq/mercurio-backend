"""
app/services/reservaciones_vencidas_scheduler.py
Loop periódico que cancela las reservaciones que no se liquidaron a tiempo.

Regla de negocio: un evento debe quedar pagado por completo a más tardar una
semana antes de su fecha. Si llega ese plazo con saldo pendiente, la reservación
se cancela por falta de pago y la fecha queda libre para otro cliente.

Se ejecuta como loop y no como consulta al vuelo porque la cancelación tiene que
ocurrir aunque nadie abra la aplicación: la fecha se libera sola.

Alcance deliberadamente acotado: sólo eventos que aún no ocurren. Ver
`listar_vencidas_sin_liquidar()` para el porqué.
"""

from __future__ import annotations

import asyncio
import logging

import asyncpg

from app.core.database import get_pool
from app.repositories import reservaciones_repository

logger = logging.getLogger("mercury.reservaciones_vencidas_scheduler")

# Plazo de liquidación: el evento debe estar pagado esta cantidad de días antes.
DIAS_LIMITE_LIQUIDACION = 7

# Una hora. El plazo se mide en días, así que revisar más seguido no adelanta
# ninguna cancelación y sólo agrega consultas.
INTERVALO_SEGUNDOS = 3600

MOTIVO = "Cancelada automáticamente: no se liquidó una semana antes del evento."


async def revisar_reservaciones_vencidas(conn: asyncpg.Connection) -> int:
    """Cancela las reservaciones vencidas sin liquidar. Devuelve cuántas canceló."""
    vencidas = await reservaciones_repository.listar_vencidas_sin_liquidar(
        conn, DIAS_LIMITE_LIQUIDACION
    )
    if not vencidas:
        return 0

    canceladas = 0
    for reservacion in vencidas:
        adeudo = reservacion["precio_total"] - reservacion["anticipo"]
        try:
            await reservaciones_repository.cancelar_por_falta_de_pago(
                conn, reservacion["id"], MOTIVO
            )
        except Exception:
            # Una reservación que falle no debe impedir cancelar las demás.
            logger.exception(
                "No se pudo cancelar la reservación %s por falta de pago.", reservacion["id"]
            )
            continue

        canceladas += 1
        # Se registra cada cancelación con su adeudo: es dinero que se deja de
        # esperar y una fecha que se libera, así que debe quedar rastro fuera
        # de la propia fila.
        logger.warning(
            "Reservación %s cancelada por falta de pago. Cliente: %s · Evento: %s · Adeudo: %s",
            reservacion["id"],
            reservacion["nombre_cliente"],
            reservacion["fecha_evento"],
            adeudo,
        )

    return canceladas


async def loop_reservaciones_vencidas() -> None:
    while True:
        try:
            pool = get_pool()
            async with pool.acquire() as conn:
                canceladas = await revisar_reservaciones_vencidas(conn)
                if canceladas:
                    logger.warning(
                        "%s reservación(es) cancelada(s) por no liquidarse a tiempo.", canceladas
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Error inesperado en el loop de reservaciones vencidas.")
        await asyncio.sleep(INTERVALO_SEGUNDOS)
