"""Verifica que _calcular_balance suma el ingreso de efectivo al esperado
(a diferencia del retiro/cambio, que restan)."""
import uuid
from decimal import Decimal

from app.repositories import caja_repository
from app.services import turnos_caja_service
from tests.integration.conftest import EFECTIVO_ID


async def test_calcular_balance_suma_el_ingreso_al_esperado(conn, apertura_prueba):
    referencia_venta = str(uuid.uuid4())
    await caja_repository.registrar_movimiento_caja(
        conn,
        apertura_caja_id=apertura_prueba,
        tipo_movimiento="O",
        referencia_id=referencia_venta,
        metodo_pago_id=EFECTIVO_ID,
        monto=Decimal("200.00"),
    )
    await caja_repository.registrar_ingreso_efectivo(
        conn,
        apertura_caja_id=apertura_prueba,
        referencia_id=apertura_prueba,
        monto=Decimal("500.00"),
    )

    apertura = await caja_repository.get_apertura_por_id(conn, apertura_prueba)

    total_esperado, _total_declarado, _diferencia, _balance = await turnos_caja_service._calcular_balance(
        conn, apertura, apertura_prueba
    )

    # fondo_inicial (1000.00, fijado por la fixture) + venta (200.00) + ingreso (500.00) = 1700.00
    assert total_esperado == Decimal("1700.00")
