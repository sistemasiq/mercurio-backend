"""Pendiente B9 B.1: últimos 4 dígitos de la tarjeta, opcionales, en el pago
de una comanda."""

from decimal import Decimal
from uuid import uuid4

import pytest
from app.schemas.pagos import PaymentItem
from pydantic import ValidationError


def test_ultimos4_opcional_por_default():
    item = PaymentItem(metodo_pago_id=uuid4(), monto=Decimal("100"))
    assert item.ultimos4 is None


def test_acepta_cuatro_digitos():
    item = PaymentItem(metodo_pago_id=uuid4(), monto=Decimal("100"), ultimos4="1234")
    assert item.ultimos4 == "1234"


def test_vacio_se_normaliza_a_none():
    item = PaymentItem(metodo_pago_id=uuid4(), monto=Decimal("100"), ultimos4="")
    assert item.ultimos4 is None


def test_rechaza_no_numerico():
    with pytest.raises(ValidationError):
        PaymentItem(metodo_pago_id=uuid4(), monto=Decimal("100"), ultimos4="12ab")


def test_rechaza_longitud_distinta_de_cuatro():
    with pytest.raises(ValidationError):
        PaymentItem(metodo_pago_id=uuid4(), monto=Decimal("100"), ultimos4="123")
