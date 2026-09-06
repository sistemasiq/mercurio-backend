"""Verifica que _calcular_balance resta el cambio dado del efectivo
esperado."""
import uuid
from decimal import Decimal

from app.repositories import caja_repository
from app.services import turnos_caja_service
from tests.integration.conftest import EFECTIVO_ID


async def test_calcular_balance_resta_el_cambio_del_esperado(conn, apertura_prueba):
    referencia_venta = str(uuid.uuid4())
    await caja_repository.registrar_movimiento_caja(
        conn,
        apertura_caja_id=apertura_prueba,
        tipo_movimiento="O",
        referencia_id=referencia_venta,
        metodo_pago_id=EFECTIVO_ID,
        monto=Decimal("200.00"),
    )
    await caja_repository.registrar_cambio_caja(
        conn,
        apertura_caja_id=apertura_prueba,
        referencia_id=referencia_venta,
        monto=Decimal("80.00"),
    )

    apertura = await caja_repository.get_apertura_por_id(conn, apertura_prueba)

    total_esperado, _total_declarado, _diferencia, _balance = await turnos_caja_service._calcular_balance(
        conn, apertura, apertura_prueba
    )

    # fondo_inicial (1000.00, fijado por la fixture) + venta (200.00) - cambio (80.00) = 1120.00
    assert total_esperado == Decimal("1120.00")
