"""Pruebas unitarias de B6 (catálogos): folio de orden de compra y mensaje de
producto duplicado. Sin DB: la conexión se simula."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import asyncpg
from app.repositories.compra_repository import siguiente_folio
from app.services.producto_service import _mensaje_duplicado


async def test_folio_de_compra_usa_serie_y_relleno_de_cuatro_digitos() -> None:
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value={"serie": "OC", "ultimo": 7})

    folio = await siguiente_folio(conn, uuid4())

    assert folio == "OC-0007"
    # El UPSERT es lo que garantiza que dos altas simultáneas no repitan número.
    sql = conn.fetchrow.call_args.args[0]
    assert "ON CONFLICT (sucursal_id)" in sql


async def test_folio_de_compra_no_trunca_numeros_grandes() -> None:
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value={"serie": "OC", "ultimo": 12345})

    assert await siguiente_folio(conn, uuid4()) == "OC-12345"


def test_duplicado_por_codigo_lo_dice_explicitamente() -> None:
    exc = asyncpg.UniqueViolationError("duplicate key")
    exc.constraint_name = "idx_productos_sucursal_codigo"  # type: ignore[attr-defined]

    assert "código" in _mensaje_duplicado(exc)


def test_duplicado_sin_constraint_conocido_se_reporta_como_nombre() -> None:
    exc = asyncpg.UniqueViolationError("duplicate key")
    exc.constraint_name = None  # type: ignore[attr-defined]

    assert "nombre" in _mensaje_duplicado(exc)
