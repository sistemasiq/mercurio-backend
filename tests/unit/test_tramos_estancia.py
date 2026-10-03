"""Tramos de precio de la estancia (issue #32)."""

from decimal import Decimal

from app.services.tramos_estancia import tramos_de_producto

TRAMOS = [
    {"min_horas": 1, "max_horas": 1, "precio": 150},
    {"min_horas": 2, "max_horas": 3, "precio": 125},
]


def test_usa_los_tramos_configurados() -> None:
    assert tramos_de_producto(TRAMOS, Decimal("0")) == TRAMOS


def test_acepta_tramos_serializados_como_json() -> None:
    assert tramos_de_producto('[{"min_horas": 1, "max_horas": 2, "precio": 90}]', None) == [
        {"min_horas": 1, "max_horas": 2, "precio": 90}
    ]


def test_sin_tramos_usa_el_precio_unitario_como_tramo_unico_por_hora() -> None:
    tramos = tramos_de_producto(None, Decimal("150.00"))
    assert tramos == [{"min_horas": 1, "max_horas": 100, "precio": 150.0}]


def test_lista_vacia_tambien_cae_al_precio_unitario() -> None:
    assert tramos_de_producto([], "120")[0]["precio"] == 120.0


def test_sin_tramos_ni_precio_no_inventa_un_precio() -> None:
    assert tramos_de_producto(None, Decimal("0")) == []
    assert tramos_de_producto("no es json", None) == []
