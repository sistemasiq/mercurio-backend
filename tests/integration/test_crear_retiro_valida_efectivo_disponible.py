"""Verifica que crear_retiro rechace un retiro parcial que excede el efectivo
disponible en la caja en ese momento (fondo inicial + ventas efectivo + ingresos
- retiros previos - cambio dado), en vez de permitir dejar el drawer en negativo."""

from decimal import Decimal

import pytest
from app.schemas.caja import RetiroParcialCreate, TipoDestinatario
from app.services.turnos_caja_service import EfectivoInsuficienteError, crear_retiro

from tests.integration.conftest import CAJERO_ID


async def test_retiro_que_excede_efectivo_disponible_se_rechaza(conn, apertura_prueba):
    # apertura_prueba: fondo_inicial=1000.00, sin ventas ni ingresos aún.
    payload = RetiroParcialCreate(
        apertura_caja_id=apertura_prueba,
        tipo_destinatario=TipoDestinatario.EMPLEADO,
        monto=Decimal("1500.00"),
    )
    with pytest.raises(EfectivoInsuficienteError):
        await crear_retiro(conn, CAJERO_ID, payload)


async def test_retiro_dentro_del_efectivo_disponible_se_permite(conn, apertura_prueba):
    payload = RetiroParcialCreate(
        apertura_caja_id=apertura_prueba,
        tipo_destinatario=TipoDestinatario.EMPLEADO,
        monto=Decimal("400.00"),
    )
    resp = await crear_retiro(conn, CAJERO_ID, payload)
    assert resp.monto == Decimal("400.00")


async def test_retiro_considera_retiros_previos_del_mismo_turno(conn, apertura_prueba):
    # Dos retiros de 600 sobre un fondo de 1000: el primero cabe (deja 400
    # disponibles), el segundo (600) ya no cabe -- debe rechazarse aunque
    # 600 <= 1000 (el fondo inicial), porque ya se retiraron 600 antes.
    primero = RetiroParcialCreate(
        apertura_caja_id=apertura_prueba,
        tipo_destinatario=TipoDestinatario.EMPLEADO,
        monto=Decimal("600.00"),
    )
    await crear_retiro(conn, CAJERO_ID, primero)

    segundo = RetiroParcialCreate(
        apertura_caja_id=apertura_prueba,
        tipo_destinatario=TipoDestinatario.EMPLEADO,
        monto=Decimal("600.00"),
    )
    with pytest.raises(EfectivoInsuficienteError):
        await crear_retiro(conn, CAJERO_ID, segundo)


async def test_retiro_exactamente_igual_al_disponible_se_permite(conn, apertura_prueba):
    payload = RetiroParcialCreate(
        apertura_caja_id=apertura_prueba,
        tipo_destinatario=TipoDestinatario.EMPLEADO,
        monto=Decimal("1000.00"),
    )
    resp = await crear_retiro(conn, CAJERO_ID, payload)
    assert resp.monto == Decimal("1000.00")
