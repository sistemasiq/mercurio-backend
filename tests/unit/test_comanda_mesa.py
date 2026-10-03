"""Pendiente B9 B.2: mesa del pedido, opcional, en la comanda."""

from decimal import Decimal
from uuid import uuid4

from app.schemas.comanda import ComandaCreate, EstadoComanda
from app.schemas.pagos import PagoCompletoRequest, PaymentItem


def test_comanda_create_acepta_mesa_opcional():
    data = ComandaCreate(
        detalles_comanda=[],
        ticket_numero="T0000001",
        total_final=Decimal("100"),
        mesa="M5",
    )
    assert data.mesa == "M5"


def test_comanda_create_mesa_es_none_por_default():
    data = ComandaCreate(
        detalles_comanda=[],
        ticket_numero="T0000001",
        total_final=Decimal("100"),
        estado_actual=EstadoComanda.PENDIENTE,
    )
    assert data.mesa is None


def test_pago_completo_request_acepta_mesa():
    data = PagoCompletoRequest(
        total_final=Decimal("100"),
        detalles_comanda=[],
        pagos=[PaymentItem(metodo_pago_id=uuid4(), monto=Decimal("100"))],
        mesa="Terraza 3",
    )
    assert data.mesa == "Terraza 3"
