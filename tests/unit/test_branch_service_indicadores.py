"""Pendiente B5 #6: GET /sucursales/{id}/indicadores (ventas, niños, eventos,
cajas abiertas), de solo lectura sobre tablas existentes."""

from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.schemas.auth import TokenData
from app.services import branch_service
from app.services.branch_service import BranchNotFoundError, InsufficientPermissionsError


def _token(role: str, branch_id=None) -> TokenData:
    from datetime import UTC, datetime

    return TokenData(
        sub=str(uuid4()),
        email="x@test.com",
        role=role,
        branch_id=branch_id,
        permissions=[],
        jti="jti",
        exp=datetime(2099, 1, 1, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_get_indicadores_devuelve_los_cuatro_valores():
    conn = object()
    branch_id = uuid4()
    current_user = _token("AdministradorSistema")

    with (
        patch(
            "app.services.branch_service.get_sucursal_by_id",
            AsyncMock(return_value={"id": branch_id}),
        ),
        patch(
            "app.services.branch_service.get_indicadores_sucursal",
            AsyncMock(
                return_value={
                    "ventas": 1500,
                    "ninos_atendidos": 12,
                    "eventos": 2,
                    "cajas_abiertas": 1,
                }
            ),
        ),
    ):
        result = await branch_service.get_indicadores(
            conn, branch_id, date(2026, 1, 1), date(2026, 1, 31), current_user
        )

    assert result.ventas == 1500
    assert result.ninos_atendidos == 12
    assert result.eventos == 2
    assert result.cajas_abiertas == 1


@pytest.mark.asyncio
async def test_administrador_no_puede_ver_indicadores_de_otra_sucursal():
    conn = object()
    current_user = _token("Administrador", branch_id=uuid4())

    with pytest.raises(InsufficientPermissionsError):
        await branch_service.get_indicadores(
            conn, uuid4(), date(2026, 1, 1), date(2026, 1, 31), current_user
        )


@pytest.mark.asyncio
async def test_sucursal_inexistente_lanza_not_found():
    conn = object()
    branch_id = uuid4()
    current_user = _token("AdministradorSistema")

    with (
        patch(
            "app.services.branch_service.get_sucursal_by_id",
            AsyncMock(return_value=None),
        ),
        pytest.raises(BranchNotFoundError),
    ):
        await branch_service.get_indicadores(
            conn, branch_id, date(2026, 1, 1), date(2026, 1, 31), current_user
        )
