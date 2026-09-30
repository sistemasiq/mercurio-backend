"""Verifica que el enum Python TipoMovimientoCaja está sincronizado con el
enum tipo_movimiento_caja de Postgres (migración 042 agregó 'C', migración
043 agrega 'I' del lado de la base de datos)."""
from app.models.caja import TipoMovimientoCaja


def test_incluye_cambio():
    assert TipoMovimientoCaja.CAMBIO == "C"


def test_incluye_ingreso():
    assert TipoMovimientoCaja.INGRESO == "I"


def test_todos_los_valores_conocidos():
    assert {m.value for m in TipoMovimientoCaja} == {"E", "O", "R", "RP", "C", "I"}
