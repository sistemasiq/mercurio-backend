"""Pendiente B9 A.2: el alta/edición de sucursal valida que la apertura sea
menor que el cierre (no se soporta cruce de medianoche)."""

from datetime import time

import pytest
from app.schemas.branch import BranchCreateRequest, BranchUpdateRequest
from pydantic import ValidationError


def test_create_acepta_horario_valido():
    data = BranchCreateRequest(
        nombre="Sucursal X", hora_apertura=time(8, 0), hora_cierre=time(22, 0)
    )
    assert data.hora_apertura == time(8, 0)
    assert data.hora_cierre == time(22, 0)


def test_create_usa_default_09_23_si_no_se_envia():
    data = BranchCreateRequest(nombre="Sucursal X")
    assert data.hora_apertura == time(9, 0)
    assert data.hora_cierre == time(23, 0)


def test_create_rechaza_apertura_mayor_o_igual_a_cierre():
    with pytest.raises(ValidationError):
        BranchCreateRequest(nombre="Sucursal X", hora_apertura=time(23, 0), hora_cierre=time(9, 0))

    with pytest.raises(ValidationError):
        BranchCreateRequest(nombre="Sucursal X", hora_apertura=time(10, 0), hora_cierre=time(10, 0))


def test_update_rechaza_apertura_mayor_o_igual_a_cierre():
    with pytest.raises(ValidationError):
        BranchUpdateRequest(nombre="Sucursal X", hora_apertura=time(23, 0), hora_cierre=time(9, 0))
