"""
app/services/costeo_service.py
Costeo PEPS/FIFO de insumos. Cada entrada de stock crea una capa con su costo;
cada consumo agota las capas más viejas primero y devuelve el costo consumido.
Después de cada movimiento recalcula insumos.costo_unitario como el promedio
ponderado de las capas con stock restante.

SAD §3.2: orquesta repositorios, no escribe SQL. Se llama SIEMPRE dentro de la
transacción que ya abrió el llamador (venta, compra, ajuste).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

import asyncpg

from app.repositories import capa_costo_repository, insumo_repository

logger = logging.getLogger(__name__)


async def _recalcular_costo_insumo(conn: asyncpg.Connection, insumo_id: UUID) -> None:
    promedio = await capa_costo_repository.costo_promedio(conn, insumo_id)
    await insumo_repository.actualizar(conn, insumo_id, {"costo_unitario": promedio})


async def registrar_entrada(
    conn: asyncpg.Connection,
    insumo_id: UUID,
    cantidad_base: Decimal,
    costo_unitario_base: Decimal,
    origen: str,
    referencia_id: UUID | None = None,
) -> None:
    """Crea una capa de costo por una entrada de stock ya aplicada."""
    if cantidad_base <= 0:
        return
    await capa_costo_repository.crear_capa(
        conn,
        insumo_id=insumo_id,
        cantidad=cantidad_base,
        costo_unitario=costo_unitario_base,
        origen=origen,
        referencia_id=referencia_id,
    )
    await _recalcular_costo_insumo(conn, insumo_id)


async def consumir(
    conn: asyncpg.Connection, insumo_id: UUID, cantidad_base: Decimal
) -> Decimal:
    """Agota capas FIFO por `cantidad_base` y devuelve el costo total consumido.
    Si las capas no cubren (drift entre stock_actual y las capas), valúa el
    faltante al costo promedio conocido y deja un warning."""
    if cantidad_base <= 0:
        return Decimal("0")

    restante = cantidad_base
    costo_total = Decimal("0")
    for capa in await capa_costo_repository.capas_disponibles(conn, insumo_id):
        if restante <= 0:
            break
        toma = min(restante, capa["cantidad_restante"])
        await capa_costo_repository.consumir_de_capa(conn, capa["id"], toma)
        costo_total += toma * capa["costo_unitario"]
        restante -= toma

    if restante > 0:
        costo_ref = await capa_costo_repository.costo_promedio(conn, insumo_id)
        costo_total += restante * costo_ref
        logger.warning(
            "FIFO: las capas del insumo %s no cubren %s (faltaron %s); "
            "faltante valuado al costo de referencia %s",
            insumo_id,
            cantidad_base,
            restante,
            costo_ref,
        )

    await _recalcular_costo_insumo(conn, insumo_id)
    return costo_total


async def costo_promedio_actual(conn: asyncpg.Connection, insumo_id: UUID) -> Decimal:
    return await capa_costo_repository.costo_promedio(conn, insumo_id)
