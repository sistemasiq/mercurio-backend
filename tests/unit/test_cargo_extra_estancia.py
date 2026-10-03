"""Pruebas unitarias de _calcular_cargo_extra_sync (app/services/chekouts.py):
función pura que calcula el excedente de una estancia, compartida por
cotizar_checkout (caja) y por el portal de padres (B2 #1), para que ambos no
puedan desincronizarse de la misma fórmula."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.services.chekouts import EXTRA_GRACE_MINUTES, _calcular_cargo_extra_sync

PRECIO = Decimal("50.00")


def _hace(minutos: int) -> tuple[datetime, datetime]:
    """Devuelve (salida_esperada, now) tal que `now` quedó `minutos` después
    de la salida esperada."""
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return now - timedelta(minutes=minutos), now


def test_dentro_del_tiempo_contratado_no_cobra_extra():
    salida_esperada, now = _hace(-30)  # todavía faltan 30 min
    horas, total = _calcular_cargo_extra_sync(salida_esperada, PRECIO, now)
    assert horas == 0
    assert total == 0.0


def test_dentro_de_la_tolerancia_no_cobra_extra():
    salida_esperada, now = _hace(EXTRA_GRACE_MINUTES)
    horas, total = _calcular_cargo_extra_sync(salida_esperada, PRECIO, now)
    assert horas == 0
    assert total == 0.0


def test_pasada_la_tolerancia_cobra_una_hora_completa():
    salida_esperada, now = _hace(EXTRA_GRACE_MINUTES + 1)
    horas, total = _calcular_cargo_extra_sync(salida_esperada, PRECIO, now)
    assert horas == 1
    assert total == float(PRECIO)


def test_redondea_hacia_arriba_por_hora_iniciada():
    # 70 min después de la tolerancia -> 2 horas (ceil), no 1.17
    salida_esperada, now = _hace(EXTRA_GRACE_MINUTES + 70)
    horas, total = _calcular_cargo_extra_sync(salida_esperada, PRECIO, now)
    assert horas == 2
    assert total == float(PRECIO) * 2
