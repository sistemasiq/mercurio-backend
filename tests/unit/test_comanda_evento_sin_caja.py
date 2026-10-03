"""Comandas automáticas de eventos: se crean sin movimiento de venta en caja.

El ingreso del evento ya se cobra en pagos_reservacion; registrar la comanda
en la caja lo contaría dos veces. Sin DB: repositorios y servicios simulados."""

from contextlib import asynccontextmanager
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services import comanda_evento_scheduler, comanda_service


def _conn() -> MagicMock:
    conn = MagicMock()

    @asynccontextmanager
    async def transaccion() -> Any:
        yield

    conn.transaction = transaccion
    conn.execute = AsyncMock()
    return conn


def _token() -> Any:
    return SimpleNamespace(sub=str(uuid4()))


def _comanda_in() -> Any:
    return SimpleNamespace(sucursal_id=uuid4(), detalles_comanda=[])


async def _crear(apertura_caja_id: str | None) -> AsyncMock:
    comanda = SimpleNamespace(id=str(uuid4()), total_final=100, detalles=[], sucursal_id="s")
    registrar = AsyncMock()
    with (
        patch.object(
            comanda_service.comanda_repository,
            "crear_comanda_con_detalles",
            AsyncMock(return_value=comanda),
        ),
        patch.object(comanda_service.inventario_service, "descontar_por_venta", AsyncMock()),
        patch.object(comanda_service, "registrar_movimiento_caja", registrar),
        patch.object(comanda_service, "expandir_detalles_comanda", AsyncMock(return_value=[])),
        patch.object(comanda_service.manager, "broadcast", AsyncMock()),
        patch.object(comanda_service, "asdict", lambda c: {}),
    ):
        await comanda_service.crear_comanda(_conn(), _comanda_in(), _token(), apertura_caja_id)
    return registrar


async def test_sin_turno_no_registra_movimiento_en_caja() -> None:
    registrar = await _crear(None)
    registrar.assert_not_called()


async def test_con_turno_registra_la_venta_en_su_caja() -> None:
    registrar = await _crear("apertura-1")
    registrar.assert_awaited_once()
    assert registrar.call_args.kwargs["apertura_caja_id"] == "apertura-1"


async def test_el_scheduler_crea_la_comanda_de_evento_sin_caja() -> None:
    reservacion = {
        "id": uuid4(),
        "sucursal_id": uuid4(),
        "nombre_cliente": "Ana",
        "fecha_evento": "2026-10-10",
        "hora_inicio": "16:00:00",
    }
    detalle = SimpleNamespace(subtotal=Decimal("50"))
    crear = AsyncMock(return_value=SimpleNamespace(id=str(uuid4()), ticket_numero="EVT1"))
    with (
        patch.object(
            comanda_evento_scheduler, "_armar_detalles", AsyncMock(return_value=[detalle])
        ),
        patch.object(comanda_evento_scheduler, "ComandaCreate", lambda **kw: SimpleNamespace(**kw)),
        patch.object(
            comanda_evento_scheduler, "_obtener_token_sistema", AsyncMock(return_value=_token())
        ),
        patch.object(comanda_evento_scheduler.comanda_service, "crear_comanda", crear),
        patch.object(
            comanda_evento_scheduler.reservaciones_repository, "marcar_comanda_enviada", AsyncMock()
        ),
    ):
        await comanda_evento_scheduler._procesar_reservacion(_conn(), reservacion)

    assert crear.call_args.kwargs["apertura_caja_id"] is None
