"""Verifica que obtener_ids_por_tipo resuelve la fila canónica del catálogo
global de métodos_pago (migración 037: una sola fila por tipo)."""
from uuid import UUID

from app.repositories import metodos_pago_repository
from tests.integration.conftest import EFECTIVO_ID, TARJETA_ID


async def test_obtener_ids_por_tipo_efectivo(conn):
    ids = await metodos_pago_repository.obtener_ids_por_tipo(conn, "E")
    assert ids == {UUID(EFECTIVO_ID)}


async def test_obtener_ids_por_tipo_tarjeta(conn):
    ids = await metodos_pago_repository.obtener_ids_por_tipo(conn, "T")
    assert ids == {UUID(TARJETA_ID)}


async def test_obtener_ids_por_tipo_sin_match_devuelve_vacio(conn):
    ids = await metodos_pago_repository.obtener_ids_por_tipo(conn, "X")
    assert ids == set()
