"""Pendiente B5 #1: apellidos/telefono en el usuario y 'activo' editable
desde el formulario (en vez de solo por DELETE)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.schemas.auth import TokenData
from app.schemas.user import UserUpdateRequest
from app.services import user_service

ROL_CAJERO = "Cajero"


class _FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeConn:
    def transaction(self):
        return _FakeTransaction()


def _token_data(sub: str, role: str, branch_id=None) -> TokenData:
    return TokenData(
        sub=sub,
        email="admin@test.com",
        role=role,
        branch_id=branch_id,
        permissions=[],
        jti="jti",
        exp=datetime(2099, 1, 1, tzinfo=UTC),
    )


def _usuario_record(**overrides):
    base = {
        "id": uuid4(),
        "email": "u@test.com",
        "password_hash": "hash",
        "pin_hash": None,
        "nombre_completo": "Juan",
        "apellidos": None,
        "telefono": None,
        "rol": ROL_CAJERO,
        "sucursal_id": uuid4(),
        "activo": True,
        "ultimo_acceso": None,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_update_user_pasa_apellidos_telefono_y_activo_al_repositorio():
    conn = FakeConn()
    branch_id = uuid4()
    target = _usuario_record(sucursal_id=branch_id)
    actualizado = _usuario_record(
        sucursal_id=branch_id,
        apellidos="Pérez",
        telefono="5551234567",
        activo=False,
    )
    current_user = _token_data(sub=str(uuid4()), role="AdministradorSistema", branch_id=None)

    body = UserUpdateRequest(
        email=target["email"],
        full_name=target["nombre_completo"],
        apellidos="Pérez",
        telefono="5551234567",
        role=ROL_CAJERO,
        branch_id=branch_id,
        is_active=False,
    )

    with (
        patch(
            "app.services.user_service.get_usuario_by_id",
            AsyncMock(side_effect=[target, actualizado]),
        ),
        patch(
            "app.services.user_service._assert_role_valid",
            AsyncMock(return_value=None),
        ),
        patch("app.services.user_service.email_exists", AsyncMock(return_value=False)),
        patch(
            "app.services.user_service.update_usuario", AsyncMock(return_value=True)
        ) as mock_update,
    ):
        result = await user_service.update_user(conn, target["id"], body, current_user)

    assert mock_update.await_args.kwargs["apellidos"] == "Pérez"
    assert mock_update.await_args.kwargs["telefono"] == "5551234567"
    assert mock_update.await_args.kwargs["activo"] is False
    assert result.apellidos == "Pérez"
    assert result.telefono == "5551234567"
    assert result.is_active is False


@pytest.mark.asyncio
async def test_to_response_incluye_ultimo_acceso():
    record = _usuario_record(ultimo_acceso=datetime(2026, 1, 1, tzinfo=UTC))
    response = user_service._to_response(record)
    assert response.ultimo_acceso == record["ultimo_acceso"]


# ── C1: PIN de caja ───────────────────────────────────────────────────────────


def test_to_response_tiene_pin_refleja_pin_hash():
    sin_pin = user_service._to_response(_usuario_record(pin_hash=None))
    con_pin = user_service._to_response(_usuario_record(pin_hash="hash-pin"))
    assert sin_pin.tiene_pin is False
    assert con_pin.tiene_pin is True


@pytest.mark.asyncio
async def test_create_user_hashea_pin_si_lo_manda():
    from app.schemas.user import UserCreateRequest

    conn = FakeConn()
    creado = _usuario_record(pin_hash="hash-generado")
    current_user = _token_data(sub=str(uuid4()), role="AdministradorSistema", branch_id=None)
    body = UserCreateRequest(
        email="nuevo@test.com",
        full_name="Nuevo",
        password="contraseña123",
        role=ROL_CAJERO,
        branch_id=creado["sucursal_id"],
        pin="1234",
    )

    with (
        patch("app.services.user_service._assert_role_valid", AsyncMock(return_value=None)),
        patch("app.services.user_service.email_exists", AsyncMock(return_value=False)),
        patch(
            "app.services.user_service.create_usuario",
            AsyncMock(return_value=creado["id"]),
        ) as mock_create,
        patch("app.services.user_service.assign_usuario_to_branch", AsyncMock()),
        patch("app.services.user_service.get_usuario_by_id", AsyncMock(return_value=creado)),
    ):
        result = await user_service.create_user(conn, body, current_user)

    assert mock_create.await_args.kwargs["pin_hash"] is not None
    assert result.tiene_pin is True


@pytest.mark.asyncio
async def test_update_user_no_toca_pin_si_no_lo_manda():
    conn = FakeConn()
    branch_id = uuid4()
    target = _usuario_record(sucursal_id=branch_id, pin_hash="hash-viejo")
    current_user = _token_data(sub=str(uuid4()), role="AdministradorSistema", branch_id=None)
    body = UserUpdateRequest(
        email=target["email"],
        full_name=target["nombre_completo"],
        role=ROL_CAJERO,
        branch_id=branch_id,
    )

    with (
        patch(
            "app.services.user_service.get_usuario_by_id",
            AsyncMock(side_effect=[target, target]),
        ),
        patch("app.services.user_service._assert_role_valid", AsyncMock(return_value=None)),
        patch("app.services.user_service.email_exists", AsyncMock(return_value=False)),
        patch(
            "app.services.user_service.update_usuario", AsyncMock(return_value=True)
        ) as mock_update,
    ):
        await user_service.update_user(conn, target["id"], body, current_user)

    assert mock_update.await_args.kwargs["pin_hash"] is None


@pytest.mark.asyncio
async def test_cambiar_mi_pin_con_pin_vigente_correcto():
    from app.core.security import hash_password
    from app.schemas.user import CambiarMiPinRequest

    conn = FakeConn()
    user_id = uuid4()
    target = _usuario_record(id=user_id, pin_hash=hash_password("1111"))
    body = CambiarMiPinRequest(actual="1111", pin_nuevo="2222")

    with (
        patch(
            "app.services.user_service.get_usuario_by_id",
            AsyncMock(return_value=target),
        ),
        patch(
            "app.services.user_service.update_usuario", AsyncMock(return_value=True)
        ) as mock_update,
    ):
        result = await user_service.cambiar_mi_pin(conn, user_id, body)

    assert result.ok is True
    assert mock_update.await_args.kwargs["pin_hash"] is not None


@pytest.mark.asyncio
async def test_cambiar_mi_pin_sin_pin_acepta_password():
    from app.core.security import hash_password
    from app.schemas.user import CambiarMiPinRequest

    conn = FakeConn()
    user_id = uuid4()
    target = _usuario_record(
        id=user_id, pin_hash=None, password_hash=hash_password("miPassword123")
    )
    body = CambiarMiPinRequest(actual="miPassword123", pin_nuevo="4321")

    with (
        patch(
            "app.services.user_service.get_usuario_by_id",
            AsyncMock(return_value=target),
        ),
        patch("app.services.user_service.update_usuario", AsyncMock(return_value=True)),
    ):
        result = await user_service.cambiar_mi_pin(conn, user_id, body)

    assert result.ok is True


@pytest.mark.asyncio
async def test_cambiar_mi_pin_credencial_actual_invalida():
    from app.core.security import hash_password
    from app.schemas.user import CambiarMiPinRequest

    conn = FakeConn()
    user_id = uuid4()
    target = _usuario_record(id=user_id, pin_hash=None, password_hash=hash_password("real123"))
    body = CambiarMiPinRequest(actual="lo-que-sea", pin_nuevo="9999")

    with patch(
        "app.services.user_service.get_usuario_by_id",
        AsyncMock(return_value=target),
    ):
        with pytest.raises(user_service.CredencialActualInvalidaError):
            await user_service.cambiar_mi_pin(conn, user_id, body)
