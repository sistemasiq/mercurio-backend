"""Pruebas unitarias de app.services.lealtad_service con mocks del
repository (sin BD). Cubren el ajuste manual de puntos (WP B4), el mínimo de
canje y el KPI de puntos por vencer."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.exceptions import DatosInvalidos, SaldoInsuficienteError
from app.schemas.auth import TokenData
from app.services import lealtad_service

SUCURSAL = uuid4()
USUARIO = uuid4()
CELULAR = "5512345678"


def _usuario(rol: str = "Administrador") -> TokenData:
    return TokenData(
        sub=str(USUARIO),
        email="admin@test.local",
        role=rol,
        branch_id=SUCURSAL,
        permissions=[],
        jti="jti",
        exp=datetime.now(UTC),
    )


def _config(**overrides):
    base = {
        "sucursal_id": SUCURSAL,
        "porcentaje_retorno": 1.0,
        "dias_caducidad": 30,
        "valor_punto": 1.0,
        "activo": True,
        "otorga_puntos_comandas": True,
        "otorga_puntos_reservaciones": True,
        "otorga_puntos_checkin": True,
        "minimo_canje": 0,
    }
    base.update(overrides)
    return base


def _lote(puntos_disponibles: int, lote_id=None):
    return {
        "id": lote_id or uuid4(),
        "puntos_disponibles": puntos_disponibles,
        "fecha_caducidad": None,
    }


@pytest.mark.asyncio
async def test_ajustar_puntos_positivo_crea_lote_y_movimiento(monkeypatch):
    conn = AsyncMock()
    monkeypatch.setattr(
        lealtad_service.lealtad_repository,
        "obtener_configuracion",
        AsyncMock(return_value=_config()),
    )
    monkeypatch.setattr(
        lealtad_service.lealtad_repository,
        "crear_lote",
        AsyncMock(return_value={"id": uuid4()}),
    )
    monkeypatch.setattr(
        lealtad_service.lealtad_repository, "calcular_saldo", AsyncMock(return_value=150)
    )
    movimiento_id = uuid4()
    monkeypatch.setattr(
        lealtad_service.lealtad_repository,
        "registrar_movimiento_devolviendo",
        AsyncMock(
            return_value={
                "id": movimiento_id,
                "sucursal_id": SUCURSAL,
                "celular": CELULAR,
                "lote_id": uuid4(),
                "comanda_id": None,
                "tipo": "A",
                "puntos": 100,
                "saldo_resultante": 150,
                "notas": "regalo por cumpleaños",
                "creado": datetime.now(UTC),
                "creado_por": USUARIO,
            }
        ),
    )

    resultado = await lealtad_service.ajustar_puntos(
        conn, _usuario(), None, CELULAR, 100, "regalo por cumpleaños"
    )

    assert resultado.puntos == 100
    assert resultado.tipo == "A"
    lealtad_service.lealtad_repository.crear_lote.assert_awaited_once()


@pytest.mark.asyncio
async def test_ajustar_puntos_negativo_descuenta_de_lotes_vigentes(monkeypatch):
    conn = AsyncMock()
    lote_id = uuid4()
    monkeypatch.setattr(
        lealtad_service.lealtad_repository,
        "lotes_vigentes_for_update",
        AsyncMock(return_value=[_lote(80, lote_id)]),
    )
    monkeypatch.setattr(
        lealtad_service.lealtad_repository, "descontar_lote", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        lealtad_service.lealtad_repository,
        "registrar_movimiento_devolviendo",
        AsyncMock(
            return_value={
                "id": uuid4(),
                "sucursal_id": SUCURSAL,
                "celular": CELULAR,
                "lote_id": lote_id,
                "comanda_id": None,
                "tipo": "A",
                "puntos": -30,
                "saldo_resultante": 50,
                "notas": "corrección de captura",
                "creado": datetime.now(UTC),
                "creado_por": USUARIO,
            }
        ),
    )

    resultado = await lealtad_service.ajustar_puntos(
        conn, _usuario(), None, CELULAR, -30, "corrección de captura"
    )

    assert resultado.puntos == -30
    lealtad_service.lealtad_repository.descontar_lote.assert_awaited_once_with(conn, lote_id, 30)


@pytest.mark.asyncio
async def test_ajustar_puntos_negativo_sin_saldo_suficiente_lanza_error(monkeypatch):
    conn = AsyncMock()
    monkeypatch.setattr(
        lealtad_service.lealtad_repository,
        "lotes_vigentes_for_update",
        AsyncMock(return_value=[_lote(10)]),
    )

    with pytest.raises(SaldoInsuficienteError):
        await lealtad_service.ajustar_puntos(conn, _usuario(), None, CELULAR, -30, "ajuste")


@pytest.mark.asyncio
async def test_redimir_puntos_rechaza_si_no_alcanza_el_minimo_de_canje(monkeypatch):
    conn = AsyncMock()
    monkeypatch.setattr(
        lealtad_service.lealtad_repository,
        "obtener_configuracion",
        AsyncMock(return_value=_config(minimo_canje=100)),
    )
    monkeypatch.setattr(
        lealtad_service.lealtad_repository,
        "lotes_vigentes_for_update",
        AsyncMock(return_value=[_lote(50)]),
    )

    with pytest.raises(DatosInvalidos):
        await lealtad_service.redimir_puntos(conn, SUCURSAL, CELULAR, 20, None, USUARIO)


@pytest.mark.asyncio
async def test_consultar_saldo_incluye_por_vencer(monkeypatch):
    conn = AsyncMock()
    monkeypatch.setattr(
        lealtad_service.lealtad_repository, "calcular_saldo", AsyncMock(return_value=200)
    )
    monkeypatch.setattr(
        lealtad_service.lealtad_repository, "calcular_por_vencer", AsyncMock(return_value=45)
    )

    resultado = await lealtad_service.consultar_saldo(conn, _usuario(), None, CELULAR)

    assert resultado.saldo == 200
    assert resultado.por_vencer == 45
    lealtad_service.lealtad_repository.calcular_por_vencer.assert_awaited_once_with(
        conn, SUCURSAL, CELULAR, lealtad_service.DIAS_POR_VENCER
    )


@pytest.mark.asyncio
async def test_buscar_clientes_delega_en_el_repository(monkeypatch):
    conn = AsyncMock()
    monkeypatch.setattr(
        lealtad_service.lealtad_repository,
        "buscar_clientes",
        AsyncMock(return_value=[{"celular": CELULAR, "nombre": "Ana López", "saldo": 30}]),
    )

    resultado = await lealtad_service.buscar_clientes(conn, _usuario(), None, "ana")

    assert len(resultado) == 1
    assert resultado[0].celular == CELULAR
    assert resultado[0].nombre == "Ana López"
