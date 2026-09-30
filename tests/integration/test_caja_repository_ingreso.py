"""Verifica que el ingreso de efectivo se excluye de las ventas y se puede
sumar aparte (a diferencia de retiro/cambio, que restan del efectivo
esperado, el ingreso suma)."""
import uuid
from decimal import Decimal

from app.repositories import caja_repository
from tests.integration.conftest import EFECTIVO_ID


async def test_ingreso_se_excluye_de_las_ventas_pero_se_puede_sumar_aparte(conn, apertura_prueba):
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

    total_ventas = await caja_repository.sumar_total_ventas_apertura(conn, apertura_prueba)
    total_ingresos = await caja_repository.sumar_ingresos_por_apertura(conn, apertura_prueba)
    total_efectivo = await caja_repository.sumar_ventas_efectivo_apertura(conn, apertura_prueba)

    assert total_ventas == Decimal("200.00")  # el ingreso NO se suma como venta
    assert total_ingresos == Decimal("500.00")
    assert total_efectivo == Decimal("200.00")  # tampoco infla las "ventas en efectivo"

    fila_ingreso = await conn.fetchrow(
        """
        SELECT metodo_pago_id, tipo_movimiento, monto
        FROM public.movimientos_caja
        WHERE apertura_caja_id = $1 AND tipo_movimiento = 'I'
        """,
        uuid.UUID(apertura_prueba),
    )
    assert fila_ingreso["metodo_pago_id"] is None  # mismo criterio que retiro/cambio
    assert fila_ingreso["monto"] == Decimal("500.00")
