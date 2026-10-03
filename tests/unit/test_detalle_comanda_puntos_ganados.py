"""Pendiente B9 B.3: puntos_ganados en el detalle de la orden, via join a
movimientos_puntos. null cuando no hay movimiento de otorgamiento."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from app.repositories import pago_repository

COMANDA_ID = "11111111-1111-1111-1111-111111111111"


def _comanda_row():
    return {
        "comanda_id": COMANDA_ID,
        "ticket_numero": "TICKET-1",
        "total_final": 120.0,
        "estado_actual": "T",
        "fecha_hora": datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
        "motivo_cancelacion": None,
        "creado_por_nombre": "Juan Pérez",
    }


@pytest.mark.asyncio
async def test_puntos_ganados_viene_de_movimientos_puntos():
    conn = AsyncMock()
    conn.fetchrow.return_value = _comanda_row()
    conn.fetch.side_effect = [
        [{"metodo_pago_nombre": "Efectivo", "monto": 120.0, "notas_pago": None, "ultimos4": None}],
        [],
    ]
    conn.fetchval.return_value = 12

    detalle = await pago_repository.detalle_por_comanda(conn, COMANDA_ID)

    assert detalle is not None
    assert detalle["puntos_ganados"] == 12
    conn.fetchval.assert_awaited_once_with(
        pago_repository._SELECT_PUNTOS_GANADOS_COMANDA, COMANDA_ID
    )


@pytest.mark.asyncio
async def test_puntos_ganados_es_null_sin_movimiento():
    conn = AsyncMock()
    conn.fetchrow.return_value = _comanda_row()
    conn.fetch.side_effect = [
        [{"metodo_pago_nombre": "Efectivo", "monto": 120.0, "notas_pago": None, "ultimos4": None}],
        [],
    ]
    conn.fetchval.return_value = None

    detalle = await pago_repository.detalle_por_comanda(conn, COMANDA_ID)

    assert detalle is not None
    assert detalle["puntos_ganados"] is None
