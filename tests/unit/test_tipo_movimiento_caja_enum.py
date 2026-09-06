"""Verifica que el enum Python TipoMovimientoCaja está sincronizado con el
enum tipo_movimiento_caja de Postgres (migración 042 ya agregó 'C' del lado
de la base de datos)."""
from app.models.caja import TipoMovimientoCaja


def test_incluye_cambio():
    assert TipoMovimientoCaja.CAMBIO == "C"


def test_todos_los_valores_conocidos():
    assert {m.value for m in TipoMovimientoCaja} == {"E", "O", "R", "RP", "C"}
