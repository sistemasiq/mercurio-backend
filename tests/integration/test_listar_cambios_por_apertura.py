"""Verifica que listar_cambios_por_apertura expone los movimientos de cambio
para trazabilidad en el arqueo -- mismo patrón que listar_retiros_por_apertura."""
import uuid
from decimal import Decimal

from app.repositories import caja_repository


async def test_lista_los_movimientos_de_cambio_del_turno(conn, apertura_prueba):
    referencia = str(uuid.uuid4())
    await caja_repository.registrar_cambio_caja(
        conn, apertura_caja_id=apertura_prueba, referencia_id=referencia, monto=Decimal("80.00")
    )

    cambios = await caja_repository.listar_cambios_por_apertura(conn, apertura_prueba)

    assert len(cambios) == 1
    assert cambios[0]["monto"] == Decimal("80.00")
    assert "id" in cambios[0] and "creado" in cambios[0]


async def test_turno_sin_cambio_devuelve_lista_vacia(conn, apertura_prueba):
    cambios = await caja_repository.listar_cambios_por_apertura(conn, apertura_prueba)
    assert cambios == []
