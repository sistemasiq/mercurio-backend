"""Unit tests de app.services.pagos_reservacion._resolver_tipo: distingue
anticipo / pago / liquidación (pendiente "Distinguir anticipo de
liquidación", migración 054)."""

from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from app.repositories import pagos_reservacion_repository, reservaciones_repository
from app.services import pagos_reservacion

RESERVACION_ID = uuid4()


def _reservacion(precio_total: str) -> dict:
    return {"id": RESERVACION_ID, "precio_total": Decimal(precio_total)}


@pytest.mark.asyncio
async def test_respeta_tipo_solicitado_si_no_liquida(monkeypatch):
    monkeypatch.setattr(
        reservaciones_repository, "obtener", AsyncMock(return_value=_reservacion("1000.00"))
    )
    monkeypatch.setattr(
        pagos_reservacion_repository, "sumar_pagos", AsyncMock(return_value=Decimal("0"))
    )

    tipo = await pagos_reservacion._resolver_tipo(
        AsyncMock(), RESERVACION_ID, Decimal("300.00"), "anticipo"
    )

    assert tipo == "anticipo"


@pytest.mark.asyncio
async def test_default_a_pago_si_no_se_solicita_nada(monkeypatch):
    monkeypatch.setattr(
        reservaciones_repository, "obtener", AsyncMock(return_value=_reservacion("1000.00"))
    )
    monkeypatch.setattr(
        pagos_reservacion_repository, "sumar_pagos", AsyncMock(return_value=Decimal("300.00"))
    )

    tipo = await pagos_reservacion._resolver_tipo(
        AsyncMock(), RESERVACION_ID, Decimal("200.00"), None
    )

    assert tipo == "pago"


@pytest.mark.asyncio
async def test_fuerza_liquidacion_si_el_pago_deja_el_saldo_en_cero(monkeypatch):
    """Aun pidiendo 'anticipo' (p.ej. quien liquida el 100% desde
    NuevaReservacionPage.vue), el backend lo sobreescribe a 'liquidacion' si
    el saldo llega a 0 -- regla explícita del pendiente."""
    monkeypatch.setattr(
        reservaciones_repository, "obtener", AsyncMock(return_value=_reservacion("1000.00"))
    )
    monkeypatch.setattr(
        pagos_reservacion_repository, "sumar_pagos", AsyncMock(return_value=Decimal("700.00"))
    )

    tipo = await pagos_reservacion._resolver_tipo(
        AsyncMock(), RESERVACION_ID, Decimal("300.00"), "anticipo"
    )

    assert tipo == "liquidacion"


@pytest.mark.asyncio
async def test_fuerza_liquidacion_tambien_en_sobrepago(monkeypatch):
    monkeypatch.setattr(
        reservaciones_repository, "obtener", AsyncMock(return_value=_reservacion("1000.00"))
    )
    monkeypatch.setattr(
        pagos_reservacion_repository, "sumar_pagos", AsyncMock(return_value=Decimal("700.00"))
    )

    tipo = await pagos_reservacion._resolver_tipo(
        AsyncMock(), RESERVACION_ID, Decimal("500.00"), "pago"
    )

    assert tipo == "liquidacion"


@pytest.mark.asyncio
async def test_sin_reservacion_respeta_lo_solicitado(monkeypatch):
    """Si la reservación no existe (no debería pasar en producción, crear()
    la valida antes), no se intenta calcular el saldo: se usa lo pedido."""
    monkeypatch.setattr(reservaciones_repository, "obtener", AsyncMock(return_value=None))

    tipo = await pagos_reservacion._resolver_tipo(
        AsyncMock(), UUID(int=0), Decimal("100.00"), "anticipo"
    )

    assert tipo == "anticipo"
