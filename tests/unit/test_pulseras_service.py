"""Pruebas unitarias de app.services.pulseras: con mocks del repository (sin
DB). Cubre asignada_a (B2 #3), el nombre del nino o tutor que tiene la
pulsera cuando esta en uso."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.services import pulseras as pulseras_service

SUCURSAL_ID = uuid4()


@pytest.mark.asyncio
async def test_listar_todas_expone_asignada_a_cuando_esta_en_uso():
    fila = {
        "id": uuid4(),
        "sucursal_id": SUCURSAL_ID,
        "pulsera_rfid": "RFID-1",
        "activo": True,
        "usada": True,
        "asignada_a": "Juan Pérez",
        "numero_lote": None,
        "creado": None,
        "creado_por": None,
        "modificado": None,
        "modificado_por": None,
    }
    with patch("app.repositories.pulseras.listar_todas", new=AsyncMock(return_value=[fila])):
        resultado = await pulseras_service.listar_todas(conn=None, sucursal_id=SUCURSAL_ID)

    assert len(resultado) == 1
    assert resultado[0].asignada_a == "Juan Pérez"


@pytest.mark.asyncio
async def test_listar_todas_asignada_a_nulo_cuando_esta_disponible():
    fila = {
        "id": uuid4(),
        "sucursal_id": SUCURSAL_ID,
        "pulsera_rfid": "RFID-2",
        "activo": True,
        "usada": False,
        "asignada_a": None,
        "numero_lote": None,
        "creado": None,
        "creado_por": None,
        "modificado": None,
        "modificado_por": None,
    }
    with patch("app.repositories.pulseras.listar_todas", new=AsyncMock(return_value=[fila])):
        resultado = await pulseras_service.listar_todas(conn=None, sucursal_id=SUCURSAL_ID)

    assert resultado[0].usada is False
    assert resultado[0].asignada_a is None
