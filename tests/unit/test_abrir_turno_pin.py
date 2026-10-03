"""C1 #2: abrir turno exige el PIN del cajero (o su contraseña, mientras no
tenga PIN configurado), igual que ya se exige en el cierre."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.core.security import hash_password
from app.schemas.caja import AbrirTurnoPayload
from app.services import turnos_caja_service
from fastapi import HTTPException

CAJERO_ID = str(uuid4())
SUCURSAL_ID = str(uuid4())


def _cajero_row(**overrides):
    base = {
        "id": CAJERO_ID,
        "email": "cajero@test.com",
        "password_hash": hash_password("contraseña123"),
        "pin_hash": None,
        "nombre_completo": "Cajero Uno",
        "apellidos": None,
        "telefono": None,
        "rol": "Cajero",
        "sucursal_id": SUCURSAL_ID,
        "activo": True,
        "ultimo_acceso": None,
    }
    base.update(overrides)
    return base


async def _sin_turno_activo(*_args, **_kwargs):
    return None


@pytest.mark.asyncio
async def test_abrir_turno_sin_pin_lanza_422():
    conn = object()
    payload = AbrirTurnoPayload(fondo_inicial=Decimal("500.00"), sucursal_id=SUCURSAL_ID)

    with patch(
        "app.services.turnos_caja_service.get_apertura_activa_por_usuario",
        AsyncMock(return_value=None),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await turnos_caja_service.abrir_turno(conn, CAJERO_ID, None, payload)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "PIN_REQUERIDO"


@pytest.mark.asyncio
async def test_abrir_turno_con_pin_incorrecto_lanza_401():
    conn = object()
    payload = AbrirTurnoPayload(
        fondo_inicial=Decimal("500.00"), sucursal_id=SUCURSAL_ID, pin="0000"
    )
    cajero = _cajero_row(pin_hash=hash_password("1234"))

    with (
        patch(
            "app.services.turnos_caja_service.get_apertura_activa_por_usuario",
            AsyncMock(return_value=None),
        ),
        patch(
            "app.services.turnos_caja_service.get_usuario_by_id",
            AsyncMock(return_value=cajero),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await turnos_caja_service.abrir_turno(conn, CAJERO_ID, None, payload)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "CREDENCIALES_INVALIDAS"


@pytest.mark.asyncio
async def test_abrir_turno_sin_pin_configurado_acepta_password():
    conn = object()
    payload = AbrirTurnoPayload(
        fondo_inicial=Decimal("500.00"), sucursal_id=SUCURSAL_ID, pin="contraseña123"
    )
    cajero = _cajero_row(pin_hash=None)

    with (
        patch(
            "app.services.turnos_caja_service.get_apertura_activa_por_usuario",
            AsyncMock(return_value=None),
        ),
        patch(
            "app.services.turnos_caja_service.get_usuario_by_id",
            AsyncMock(return_value=cajero),
        ),
        patch(
            "app.services.turnos_caja_service.get_caja_por_codigo",
            AsyncMock(return_value={"id": str(uuid4())}),
        ),
        patch(
            "app.services.turnos_caja_service.get_apertura_activa_por_caja",
            AsyncMock(return_value=None),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await turnos_caja_service.abrir_turno(conn, CAJERO_ID, None, payload)

    # La contraseña es válida como PIN: debe pasar la validación de
    # credenciales y fallar más adelante por falta de turno_id, no por PIN.
    assert exc_info.value.detail["code"] == "TURNO_REQUERIDO"
