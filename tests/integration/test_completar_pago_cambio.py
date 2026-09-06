"""Verifica que completar_pago() registra el cambio (tipo 'C') cuando el
pago en efectivo excede el total. Los colaboradores de otros módulos
(creación de comanda, descuento de inventario, notificación a cocina) se
sustituyen por dobles de prueba -- no son responsabilidad de Cierre de Caja
y fabricar un catálogo de productos/insumos real no aporta nada a esta
prueba."""
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.models.comanda import Comanda
from app.repositories import caja_repository, comanda_repository
from app.schemas.pagos import PagoCompletoRequest, PaymentItem
from app.services import comanda_service, inventario_service, pago_service
from app.core import ws_manager
from tests.integration.conftest import EFECTIVO_ID

SUCURSAL_ID = "5e16533e-8d60-453a-9708-306bd64ad326"
CAJERO_ID = "0c81cb1e-8627-469b-abc2-f4198526e2a8"


async def test_completar_pago_registra_el_cambio_cuando_excede_el_total(
    conn, apertura_prueba, monkeypatch
):
    comanda_falsa = Comanda(
        id=str(uuid.uuid4()),
        ticket_numero="TICK-TEST",
        estado_actual="P",
        total_final=Decimal("120.00"),
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

    body = PagoCompletoRequest(
        ticket_numero="TICK-TEST",
        total_final=Decimal("120.00"),
        detalles_comanda=[],
        pagos=[PaymentItem(metodo_pago_id=UUID(EFECTIVO_ID), monto=Decimal("200.00"))],
        cambio=Decimal("80.00"),
    )

    await pago_service.completar_pago(
        conn, body, UUID(CAJERO_ID), UUID(SUCURSAL_ID), apertura_prueba
    )

    total_cambio = await caja_repository.sumar_cambio_apertura(conn, apertura_prueba)
    assert total_cambio == Decimal("80.00")
