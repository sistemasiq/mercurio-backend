"""Verifica que abrir_turno respeta la sucursal seleccionada cuando el
usuario ya tiene un turno activo en otra sucursal, en vez de cambiarlo en
silencio a la sucursal donde ya estaba abierto."""
import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.schemas.caja import AbrirTurnoPayload
from app.services import turnos_caja_service
from tests.integration.conftest import CAJA_ID, CAJERO_ID

OTRA_SUCURSAL_ID = "4103d2c8-3f6d-42ea-9643-cefc025dde0c"  # Sucursal Ciudad del Sol


async def test_abrir_turno_en_otra_sucursal_con_turno_activo_lanza_conflicto(conn, apertura_prueba):
    payload = AbrirTurnoPayload(fondo_inicial=Decimal("500.00"), sucursal_id=OTRA_SUCURSAL_ID)

    with pytest.raises(HTTPException) as exc_info:
        await turnos_caja_service.abrir_turno(conn, CAJERO_ID, None, payload)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "TURNO_ACTIVO_OTRA_SUCURSAL"


async def test_abrir_turno_en_la_misma_sucursal_con_turno_activo_lo_regresa(conn, apertura_prueba):
    row = await conn.fetchrow(
        "SELECT sucursal_id FROM public.cajas WHERE id = $1", uuid.UUID(CAJA_ID)
    )
    misma_sucursal = str(row["sucursal_id"])

    payload = AbrirTurnoPayload(fondo_inicial=Decimal("500.00"), sucursal_id=misma_sucursal)
    resultado = await turnos_caja_service.abrir_turno(conn, CAJERO_ID, None, payload)

    assert resultado.id == apertura_prueba
