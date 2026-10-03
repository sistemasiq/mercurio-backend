"""Pendiente B5 #2: el listado y el detalle de roles devuelven usuarios_count."""

from unittest.mock import AsyncMock, patch

import pytest
from app.services import permission_service


def _rol(rol_id: int, nombre: str = "Cajero"):
    return {"id": rol_id, "nombre": nombre, "descripcion": None, "activo": True}


@pytest.mark.asyncio
async def test_list_roles_asigna_el_conteo_de_cada_rol():
    conn = object()
    roles = [_rol(1, "Cajero"), _rol(2, "Cocina")]

    with (
        patch(
            "app.services.permission_service.get_all_roles",
            AsyncMock(return_value=roles),
        ),
        patch(
            "app.services.permission_service.contar_usuarios_por_rol",
            AsyncMock(return_value={1: 5}),
        ),
        patch(
            "app.services.permission_service.get_permisos_por_rol",
            AsyncMock(return_value=[]),
        ),
    ):
        result = await permission_service.list_roles(conn)

    por_id = {r.id: r.usuarios_count for r in result}
    assert por_id[1] == 5
    # Rol sin usuarios activos no aparece en el dict de conteos: default 0.
    assert por_id[2] == 0


@pytest.mark.asyncio
async def test_get_rol_consulta_el_conteo_individual():
    conn = object()
    rol = _rol(3, "Administrador")

    with (
        patch(
            "app.services.permission_service.get_rol_by_id",
            AsyncMock(return_value=rol),
        ),
        patch(
            "app.services.permission_service.get_permisos_por_rol",
            AsyncMock(return_value=[]),
        ),
        patch(
            "app.services.permission_service.contar_usuarios_de_rol",
            AsyncMock(return_value=7),
        ),
    ):
        result = await permission_service.get_rol(conn, 3)

    assert result.usuarios_count == 7
