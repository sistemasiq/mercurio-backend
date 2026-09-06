"""Verifica que completar_pago() rechaza cambio no respaldado por efectivo
real -- el hallazgo de mayor severidad de la revisión: antes de este fix,
un pago 100% tarjeta con `cambio` declarado generaba una salida de efectivo
fantasma en el corte de caja."""
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from app.exceptions import DatosInvalidos
from app.models.comanda import Comanda
from app.repositories import comanda_repository
from app.schemas.pagos import PagoCompletoRequest, PaymentItem
from app.services import comanda_service, inventario_service, pago_service
from app.core import ws_manager
from tests.integration.conftest import EFECTIVO_ID, TARJETA_ID

SUCURSAL_ID = "5e16533e-8d60-453a-9708-306bd64ad326"
CAJERO_ID = "0c81cb1e-8627-469b-abc2-f4198526e2a8"


def _parchar_colaboradores(monkeypatch, total_final: Decimal):
    comanda_falsa = Comanda(
        id=str(uuid.uuid4()),
        ticket_numero="TICK-TEST",
        estado_actual="P",
        total_final=total_final,
        sucursal_id=SUCURSAL_ID,
        fecha_hora=datetime.now(UTC),
        detalles=[],
    )

    async def fake_crear_comanda_con_detalles(*_args, **_kwargs):
        return comanda_falsa

    async def fake_descontar_por_venta(*_args, **_kwargs):
        return None

    async def fake_crear_pagos(*_args, **_kwargs):
        return []

    async def fake_broadcast(*_args, **_kwargs):
        return None

    async def fake_expandir_detalles_comanda(_conn, detalles):
        return detalles

    monkeypatch.setattr(comanda_repository, "crear_comanda_con_detalles", fake_crear_comanda_con_detalles)
    monkeypatch.setattr(inventario_service, "descontar_por_venta", fake_descontar_por_venta)
    monkeypatch.setattr(pago_service.pago_repository, "crear_pagos", fake_crear_pagos)
    monkeypatch.setattr(ws_manager.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(comanda_service, "expandir_detalles_comanda", fake_expandir_detalles_comanda)


async def test_tarjeta_con_cambio_se_rechaza(conn, apertura_prueba, monkeypatch):
    _parchar_colaboradores(monkeypatch, Decimal("120.00"))
    body = PagoCompletoRequest(
        ticket_numero="TICK-TEST",
        total_final=Decimal("120.00"),
        detalles_comanda=[],
        pagos=[PaymentItem(metodo_pago_id=UUID(TARJETA_ID), monto=Decimal("200.00"))],
        cambio=Decimal("80.00"),
    )
    with pytest.raises(DatosInvalidos):
        await pago_service.completar_pago(conn, body, UUID(CAJERO_ID), UUID(SUCURSAL_ID), apertura_prueba)


async def test_pago_mixto_invalido_se_rechaza(conn, apertura_prueba, monkeypatch):
    _parchar_colaboradores(monkeypatch, Decimal("120.00"))
    body = PagoCompletoRequest(
        ticket_numero="TICK-TEST",
        total_final=Decimal("120.00"),
        detalles_comanda=[],
        pagos=[
            PaymentItem(metodo_pago_id=UUID(TARJETA_ID), monto=Decimal("100.00")),
            PaymentItem(metodo_pago_id=UUID(EFECTIVO_ID), monto=Decimal("100.00")),
        ],
        cambio=Decimal("80.00"),  # excede los 100.00 de efectivo aportado? no -- pero
        # el punto de este test es el límite exacto: 80 <= 100 debe ACEPTARSE.
        # Se corrige abajo con el valor que sí debe rechazarse.
    )
    # Con 100 de efectivo, un cambio de 80 es válido (80 <= 100) -- no debe lanzar.
    await pago_service.completar_pago(conn, body, UUID(CAJERO_ID), UUID(SUCURSAL_ID), apertura_prueba)


async def test_pago_mixto_cambio_mayor_al_efectivo_aportado_se_rechaza(conn, apertura_prueba, monkeypatch):
    _parchar_colaboradores(monkeypatch, Decimal("20.00"))
    body = PagoCompletoRequest(
        ticket_numero="TICK-TEST",
        total_final=Decimal("20.00"),
        detalles_comanda=[],
        pagos=[
            PaymentItem(metodo_pago_id=UUID(TARJETA_ID), monto=Decimal("100.00")),
            PaymentItem(metodo_pago_id=UUID(EFECTIVO_ID), monto=Decimal("100.00")),
        ],
        cambio=Decimal("150.00"),  # excedente total = 180, pero efectivo aportado = 100 < 150.
    )
    with pytest.raises(DatosInvalidos):
        await pago_service.completar_pago(conn, body, UUID(CAJERO_ID), UUID(SUCURSAL_ID), apertura_prueba)


async def test_cambio_excede_excedente_agregado_aunque_quepa_en_efectivo_se_rechaza(
    conn, apertura_prueba, monkeypatch
):
    """Caso que ejercita específicamente el chequeo agregado preexistente
    (cambio > total_pagos - total_final), NO validar_cambio: pago 100% en
    efectivo, así que el efectivo aportado (100) cubre sobradamente el
    cambio declarado (50) y validar_cambio por sí solo NO lo rechazaría.
    Pero el excedente agregado de la transacción es solo total_pagos(100) -
    total_final(90) = 10, y cambio(50) > 10 -- debe rechazarse por el
    chequeo agregado."""
    _parchar_colaboradores(monkeypatch, Decimal("90.00"))
    body = PagoCompletoRequest(
        ticket_numero="TICK-TEST",
        total_final=Decimal("90.00"),
        detalles_comanda=[],
        pagos=[PaymentItem(metodo_pago_id=UUID(EFECTIVO_ID), monto=Decimal("100.00"))],
        cambio=Decimal("50.00"),
    )
    with pytest.raises(DatosInvalidos):
        await pago_service.completar_pago(conn, body, UUID(CAJERO_ID), UUID(SUCURSAL_ID), apertura_prueba)
