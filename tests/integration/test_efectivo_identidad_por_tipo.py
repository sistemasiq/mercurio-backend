"""Verifica que identificar 'efectivo' depende de metodos_pago.tipo='E' (la
identidad fija e inmutable del catálogo global, migración 037) y no del
nombre de la fila, que sí es editable por un AdministradorSistema."""
import uuid
from decimal import Decimal

from app.repositories import caja_repository, metodos_pago_repository
from tests.integration.conftest import EFECTIVO_ID


async def test_sumar_ventas_efectivo_ignora_el_nombre_renombrado(conn, apertura_prueba):
    nombre_original = await conn.fetchval(
        "SELECT nombre FROM metodos_pago WHERE id = $1", uuid.UUID(EFECTIVO_ID)
    )
    await metodos_pago_repository.actualizar_catalogo(
        conn, uuid.UUID(EFECTIVO_ID), {"nombre": "Caja Chica"}
    )
    try:
        await caja_repository.registrar_movimiento_caja(
            conn,
            apertura_caja_id=apertura_prueba,
            tipo_movimiento="O",
            referencia_id=str(uuid.uuid4()),
            metodo_pago_id=EFECTIVO_ID,
            monto=Decimal("300.00"),
        )
        total_efectivo = await caja_repository.sumar_ventas_efectivo_apertura(conn, apertura_prueba)
        assert total_efectivo == Decimal("300.00")  # se sigue reconociendo aunque el nombre cambió
    finally:
        await metodos_pago_repository.actualizar_catalogo(
            conn, uuid.UUID(EFECTIVO_ID), {"nombre": nombre_original}
        )


async def test_calcular_balance_ignora_el_nombre_renombrado(conn, apertura_prueba):
    from app.repositories.caja_repository import get_apertura_por_id
    from app.services import turnos_caja_service

    nombre_original = await conn.fetchval(
        "SELECT nombre FROM metodos_pago WHERE id = $1", uuid.UUID(EFECTIVO_ID)
    )
    await metodos_pago_repository.actualizar_catalogo(
        conn, uuid.UUID(EFECTIVO_ID), {"nombre": "Caja Chica"}
    )
    try:
        await caja_repository.registrar_movimiento_caja(
            conn,
            apertura_caja_id=apertura_prueba,
            tipo_movimiento="O",
            referencia_id=str(uuid.uuid4()),
            metodo_pago_id=EFECTIVO_ID,
            monto=Decimal("300.00"),
        )
        apertura = await get_apertura_por_id(conn, apertura_prueba)
        _, _, _, balance = await turnos_caja_service._calcular_balance(conn, apertura, apertura_prueba)
        fila_efectivo = next(f for f in balance if f.metodo == "efectivo")
        # fondo_inicial (1000.00) + venta (300.00) = 1300.00 -- si el renombre
        # rompiera el reconocimiento, esta fila no incluiría los 300.00.
        assert fila_efectivo.esperado == Decimal("1300.00")
        # Y no debe aparecer una fila DUPLICADA "caja chica" tratada como método aparte.
        assert not any(f.metodo == "caja chica" for f in balance)
    finally:
        await metodos_pago_repository.actualizar_catalogo(
            conn, uuid.UUID(EFECTIVO_ID), {"nombre": nombre_original}
        )
