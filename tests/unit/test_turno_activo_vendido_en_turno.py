"""Pendiente B9 B.4: "vendido en turno" para el cajero. Mientras el turno
está abierto, GET /turnos-caja/activo expone numero_ventas y total_vendido,
sin desglose por método ni efectivo esperado (conteo a ciegas)."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.services import turnos_caja_service as svc


def _apertura_abierta():
    return {
        "id": uuid4(),
        "sucursal_id": uuid4(),
        "sucursal_nombre": "Sucursal X",
        "cajero_id": uuid4(),
        "cajero_nombre": "Cajero X",
        "terminal": "T1",
        "fondo_inicial": Decimal("500"),
        "fecha_apertura": "2026-01-01T09:00:00",
        "estado": "ABIERTA",
        "monto_declarado": None,
        "token_admin_jti": None,
    }


@pytest.mark.asyncio
async def test_turno_abierto_expone_numero_ventas_y_total_vendido_sin_desglose_esperado():
    conn = object()
    activa = _apertura_abierta()

    with (
        patch(
            "app.services.turnos_caja_service.get_apertura_activa_por_usuario",
            AsyncMock(return_value=activa),
        ),
        patch(
            "app.services.turnos_caja_service.sumar_total_ventas_apertura",
            AsyncMock(return_value=Decimal("1500.50")),
        ),
        patch(
            "app.services.turnos_caja_service.contar_ventas_apertura",
            AsyncMock(return_value=7),
        ),
        patch(
            "app.services.turnos_caja_service.sumar_retiros_por_apertura",
            AsyncMock(return_value=Decimal("0")),
        ),
        patch(
            "app.services.turnos_caja_service.sumar_ingresos_por_apertura",
            AsyncMock(return_value=Decimal("0")),
        ),
        patch(
            "app.services.turnos_caja_service.obtener_movimientos_por_metodo",
            AsyncMock(return_value=[]),
        ),
    ):
        resultado = await svc.obtener_turno_activo(conn, str(activa["cajero_id"]))

    assert resultado.numero_ventas == 7
    assert resultado.total_vendido == Decimal("1500.50")
    # Conteo a ciegas: nada de balance ni admin_email mientras el turno sigue
    # abierto (no está en BALANCE_REVELADO).
    assert resultado.balance_por_metodo == []
    assert resultado.admin_email is None
