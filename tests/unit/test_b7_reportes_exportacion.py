"""
tests/unit/test_b7_reportes_exportacion.py
B7: Reportes, filtros y exportación. Cubre:
- Filtros de caja_id/metodo_pago_id en el SQL del historial de ventas/pagos.
- KPIs agregados del historial de arqueos (resumen_historial).
- Export del historial de arqueos sin paginar (listar_historial_completo).
- KPIs de ventas/margen/merma del reporte de costo de ventas (resumen_cogs).
"""

import os
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

# turnos_caja_service importa app.core.config a nivel de módulo, que exige
# estas variables (pydantic-settings). Los demás tests unitarios nunca
# importan ese service, así que nadie las había necesitado todavía.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")
os.environ.setdefault("MINIO_ACCESS_KEY", "test-access-key")
os.environ.setdefault("MINIO_SECRET_KEY", "test-secret-key")

from app.repositories import pago_repository
from app.schemas.caja import FiltrosHistorial
from app.services import inventario_service, turnos_caja_service

SUCURSAL = "22222222-2222-2222-2222-222222222222"


def test_select_historial_acepta_filtros_de_caja_y_metodo_de_pago():
    sql = pago_repository._SELECT_HISTORIAL
    assert "ac.caja_id = $5::uuid" in sql
    assert "bool_or(v.metodo_pago_id = $6::uuid)" in sql


@pytest.mark.asyncio
async def test_historial_repository_pasa_caja_id_y_metodo_pago_id():
    conn = AsyncMock()
    conn.fetch.return_value = []
    await pago_repository.historial(
        conn,
        SUCURSAL,
        datetime(2026, 8, 20, 0, 0, tzinfo=UTC),
        "todos",
        None,
        caja_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        metodo_pago_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    )
    args = conn.fetch.call_args.args
    assert args[5] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert args[6] == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


@pytest.mark.asyncio
async def test_resumen_historial_agrega_kpis_del_periodo_completo(monkeypatch):
    fake_resumen = AsyncMock(
        return_value={
            "total_arqueos": 7,
            "total_declarado": Decimal("1000.00"),
            "total_esperado": Decimal("980.00"),
            "diferencia_neta": Decimal("20.00"),
            "arqueos_con_diferencia": 2,
        }
    )
    monkeypatch.setattr(turnos_caja_service, "resumen_historial_cierres", fake_resumen)

    resultado = await turnos_caja_service.resumen_historial(
        AsyncMock(), FiltrosHistorial(sucursal_id=SUCURSAL, fecha_desde="2026-08-01")
    )

    assert resultado.total_arqueos == 7
    assert resultado.diferencia_neta == Decimal("20.00")
    # El bug de fecha_desde/fecha_hasta nunca forwardeados al repository quedó
    # corregido: debe llegar parseado como datetime, no como el string crudo.
    _, kwargs = fake_resumen.call_args
    assert isinstance(kwargs["fecha_desde"], datetime)


@pytest.mark.asyncio
async def test_listar_historial_completo_no_pagina(monkeypatch):
    fake_listar = AsyncMock(
        return_value=[
            {
                "id": "1",
                "cajero_nombre": "Ana",
                "terminal": "CAJA 01",
                "sucursal_nombre": "Centro",
                "fecha_apertura": "2026-08-20 08:00",
                "fecha_cierre": "2026-08-20 16:00",
                "fondo_inicial": Decimal("500"),
                "total_declarado": Decimal("1200"),
                "total_esperado": Decimal("1200"),
                "diferencia_neta": Decimal("0"),
                "tiene_observaciones": False,
                "admin_nombre": "Luis",
                "tipo_cierre": "NORMAL",
            }
        ]
    )
    monkeypatch.setattr(turnos_caja_service, "listar_historial_cierres", fake_listar)

    items = await turnos_caja_service.listar_historial_completo(
        AsyncMock(), FiltrosHistorial(sucursal_id=SUCURSAL, page_size=20)
    )

    assert len(items) == 1
    _, kwargs = fake_listar.call_args
    assert kwargs["offset"] == 0
    assert kwargs["limit"] >= 1_000_000


@pytest.mark.asyncio
async def test_resumen_cogs_calcula_margen_como_ventas_menos_costo(monkeypatch):
    fake_resumen = AsyncMock(
        return_value={
            "ventas_totales": Decimal("5000.00"),
            "costo_ventas": Decimal("1800.00"),
            "margen": Decimal("3200.00"),
            "merma": Decimal("150.00"),
        }
    )
    monkeypatch.setattr(
        inventario_service.movimiento_inventario_repository,
        "resumen_costo_ventas",
        fake_resumen,
    )

    resultado = await inventario_service.resumen_cogs(AsyncMock(), SUCURSAL)

    assert resultado.ventas_totales == Decimal("5000.00")
    assert resultado.margen == Decimal("3200.00")
    assert resultado.merma == Decimal("150.00")
