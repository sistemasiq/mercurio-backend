"""
app/repositories/capa_costo_repository.py
Capas de costo FIFO por insumo. SQL crudo con asyncpg. Regla 11.1 y 11.4 SAD.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg


async def crear_capa(
    conn: asyncpg.Connection,
    *,
    insumo_id: UUID,
    cantidad: Decimal,
    costo_unitario: Decimal,
    origen: str,
    referencia_id: UUID | None,
) -> None:
    await conn.execute(
        """
        INSERT INTO public.capas_costo_insumo
            (insumo_id, cantidad_inicial, cantidad_restante, costo_unitario, origen, referencia_id)
        VALUES ($1, $2, $2, $3, $4, $5)
        """,
        insumo_id,
        cantidad,
        costo_unitario,
        origen,
        referencia_id,
    )


async def capas_disponibles(conn: asyncpg.Connection, insumo_id: UUID) -> list[dict[str, Any]]:
    """Capas con stock restante, en orden FIFO (más viejas primero). `FOR UPDATE`
    serializa consumos concurrentes del mismo insumo."""
    rows = await conn.fetch(
        """
        SELECT id, cantidad_restante, costo_unitario
        FROM public.capas_costo_insumo
        WHERE insumo_id = $1 AND cantidad_restante > 0
        ORDER BY creado ASC, id ASC
        FOR UPDATE
        """,
        insumo_id,
    )
    return [dict(r) for r in rows]


async def consumir_de_capa(conn: asyncpg.Connection, capa_id: UUID, cantidad: Decimal) -> None:
    await conn.execute(
        """
        UPDATE public.capas_costo_insumo
        SET cantidad_restante = cantidad_restante - $2
        WHERE id = $1
        """,
        capa_id,
        cantidad,
    )


async def costo_promedio(conn: asyncpg.Connection, insumo_id: UUID) -> Decimal:
    """Promedio ponderado del costo de las capas con stock restante. 0 si no hay."""
    valor = await conn.fetchval(
        """
        SELECT COALESCE(
            SUM(cantidad_restante * costo_unitario) / NULLIF(SUM(cantidad_restante), 0),
            0
        )
        FROM public.capas_costo_insumo
        WHERE insumo_id = $1 AND cantidad_restante > 0
        """,
        insumo_id,
    )
    return Decimal(str(valor)) if valor is not None else Decimal("0")


async def total_restante(conn: asyncpg.Connection, insumo_id: UUID) -> Decimal:
    """Suma del stock repartido en capas (debe igualar insumos.stock_actual).
    Se usa en pruebas para verificar el invariante FIFO."""
    valor = await conn.fetchval(
        "SELECT COALESCE(SUM(cantidad_restante), 0) "
        "FROM public.capas_costo_insumo WHERE insumo_id = $1",
        insumo_id,
    )
    return Decimal(str(valor)) if valor is not None else Decimal("0")
