"""Verifica que el cambio se registra como su propio tipo de movimiento y
nunca se cuenta como venta."""
import uuid
from decimal import Decimal

from app.repositories import caja_repository
from tests.integration.conftest import EFECTIVO_ID


async def test_cambio_se_excluye_de_las_ventas_pero_se_puede_sumar_aparte(conn, apertura_prueba):
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

    total_ventas = await caja_repository.sumar_total_ventas_apertura(conn, apertura_prueba)
    total_cambio = await caja_repository.sumar_cambio_apertura(conn, apertura_prueba)
    total_efectivo = await caja_repository.sumar_ventas_efectivo_apertura(conn, apertura_prueba)

    assert total_ventas == Decimal("200.00")  # el cambio NO se suma como venta
    assert total_cambio == Decimal("80.00")
    assert total_efectivo == Decimal("200.00")  # tampoco infla el efectivo esperado
    assert total_efectivo - total_cambio == Decimal("120.00")  # neto real en el cajón

    fila_cambio = await conn.fetchrow(
        """
        SELECT metodo_pago_id, tipo_movimiento, monto
        FROM public.movimientos_caja
        WHERE apertura_caja_id = $1 AND tipo_movimiento = 'C'
        """,
        uuid.UUID(apertura_prueba),
    )
    assert fila_cambio["metodo_pago_id"] is None  # mismo criterio que el retiro parcial
    assert fila_cambio["monto"] == Decimal("80.00")
