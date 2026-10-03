"""Pruebas unitarias de _build_nino_activo (app/services/padres_service.py):
agrega cargoExtra en visitas activas e importe/puntosGanados en terminadas,
sin tocar la base de datos (ver B2 #1 -- dict de fila simulado)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.services.padres_service import _build_nino_activo

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _hijo_base(**overrides):
    base = {
        "id": uuid4(),
        "nombreCompleto": "Juan Pérez",
        "edad": 7,
        "estadoVisita": "activo",
        "horaEntrada": NOW,
        "horaSalidaEsperada": NOW,
        "horaSalida": None,
        "minutosTranscurridos": 30,
        "minutosPagados": 60,
        "pulsera": "RFID-1",
        "precio": Decimal("50.00"),
        "cantidad": 2,
        "salidaEsperadaRaw": NOW,
        "cargoExtraCobrado": Decimal("0"),
        "puntosGanadosRegistro": 0,
    }
    base.update(overrides)
    return base


def test_visita_activa_sin_excedente_no_tiene_cargo_extra():
    hijo = _hijo_base(salidaEsperadaRaw=NOW)
    dto = _build_nino_activo(hijo, NOW)
    assert dto.estadoVisita == "activo"
    assert dto.cargoExtra == 0.0
    assert dto.importe is None
    assert dto.puntosGanados is None


def test_visita_activa_excedida_calcula_cargo_extra():
    from datetime import timedelta

    hijo = _hijo_base(salidaEsperadaRaw=NOW - timedelta(minutes=70), precio=Decimal("50.00"))
    dto = _build_nino_activo(hijo, NOW)
    assert dto.cargoExtra == 50.0  # 1 hora extra (grace de 10 min ya descontada)


def test_visita_terminada_calcula_importe_y_puntos():
    hijo = _hijo_base(
        estadoVisita="terminado",
        precio=Decimal("50.00"),
        cantidad=2,
        cargoExtraCobrado=Decimal("25.00"),
        puntosGanadosRegistro=15,
    )
    dto = _build_nino_activo(hijo, NOW)
    assert dto.estadoVisita == "terminado"
    assert dto.cargoExtra == 0.0
    assert dto.importe == 125.0  # 50*2 + 25
    assert dto.puntosGanados == 15
