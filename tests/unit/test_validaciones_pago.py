"""Pruebas unitarias de validar_cambio: sin DB, sin async -- es una función
pura. Cubre los casos adversariales de integridad de efectivo del módulo de
Caja."""
from decimal import Decimal
from uuid import uuid4

import pytest

from app.exceptions import DatosInvalidos
from app.services.validaciones_pago import validar_cambio

EFECTIVO = uuid4()
TARJETA = uuid4()
TRANSFERENCIA = uuid4()  # metodos_pago.tipo = 'O' ("Otro")
IDS_EFECTIVO = {EFECTIVO}


def test_sin_cambio_no_valida_nada():
    # cambio == 0: no hay nada que respaldar, no debe lanzar aunque no haya efectivo.
    validar_cambio([(TARJETA, Decimal("200.00"))], Decimal("0"), IDS_EFECTIVO)


def test_tarjeta_con_cambio_se_rechaza():
    with pytest.raises(DatosInvalidos):
        validar_cambio([(TARJETA, Decimal("200.00"))], Decimal("80.00"), IDS_EFECTIVO)


def test_transferencia_con_cambio_se_rechaza():
    with pytest.raises(DatosInvalidos):
        validar_cambio([(TRANSFERENCIA, Decimal("200.00"))], Decimal("80.00"), IDS_EFECTIVO)


def test_pago_mixto_valido_cambio_menor_o_igual_al_efectivo():
    # $50 tarjeta + $150 efectivo, total_final=120 -> cambio=80, respaldado por
    # los $150 de efectivo (80 <= 150).
    validar_cambio(
        [(TARJETA, Decimal("50.00")), (EFECTIVO, Decimal("150.00"))],
        Decimal("80.00"),
        IDS_EFECTIVO,
    )


def test_pago_mixto_invalido_cambio_mayor_al_efectivo_aportado():
    # $100 tarjeta + $100 efectivo, cambio declarado=150 -- el efectivo
    # aportado (100) no alcanza para ese cambio aunque el excedente total
    # (200-120=... en este caso 200-50=150) sí "cuadre" en agregado.
    with pytest.raises(DatosInvalidos):
        validar_cambio(
            [(TARJETA, Decimal("100.00")), (EFECTIVO, Decimal("100.00"))],
            Decimal("150.00"),
            IDS_EFECTIVO,
        )


def test_cambio_mayor_al_efectivo_100_por_ciento_efectivo():
    # Todo el pago es efectivo (200) pero el cambio declarado (250) excede
    # incluso lo que se pagó -- imposible físicamente.
    with pytest.raises(DatosInvalidos):
        validar_cambio([(EFECTIVO, Decimal("200.00"))], Decimal("250.00"), IDS_EFECTIVO)


def test_multiples_pagos_en_efectivo_se_suman():
    # Dos abonos en efectivo en la misma transacción (ej. el cajero registra
    # el efectivo en dos capturas) -- deben sumarse antes de comparar.
    validar_cambio(
        [(EFECTIVO, Decimal("100.00")), (EFECTIVO, Decimal("100.00"))],
        Decimal("80.00"),
        IDS_EFECTIVO,
    )
