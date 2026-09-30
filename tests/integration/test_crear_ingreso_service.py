"""Verifica las reglas de negocio del servicio crear_ingreso: registra el
ingreso sobre el turno abierto del cajero y rechaza si el turno no está en
ABIERTA (mismo criterio que crear_retiro)."""
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.repositories.caja_repository import actualizar_estado_apertura
from app.schemas.caja import IngresoEfectivoCreate
from app.services import turnos_caja_service


async def test_crear_ingreso_registra_el_movimiento_sobre_el_turno_abierto(conn, apertura_prueba):
    apertura = await turnos_caja_service.get_apertura_por_id(conn, apertura_prueba)
    payload = IngresoEfectivoCreate(apertura_caja_id=apertura_prueba, monto=Decimal("300.00"))

    resultado = await turnos_caja_service.crear_ingreso(conn, str(apertura["cajero_id"]), payload)

    assert resultado.apertura_caja_id == apertura_prueba
    assert resultado.monto == Decimal("300.00")


async def test_crear_ingreso_rechaza_si_el_turno_no_esta_abierto(conn, apertura_prueba):
    apertura = await turnos_caja_service.get_apertura_por_id(conn, apertura_prueba)
    await actualizar_estado_apertura(conn, apertura_prueba, "EN_CORTE")
    payload = IngresoEfectivoCreate(apertura_caja_id=apertura_prueba, monto=Decimal("300.00"))

    with pytest.raises(HTTPException) as exc_info:
        await turnos_caja_service.crear_ingreso(conn, str(apertura["cajero_id"]), payload)

    assert exc_info.value.status_code == 409
