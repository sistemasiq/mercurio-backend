"""Tramos de precio de la estancia infantil (issue #32).

El producto de estancia (tipo 'E') define sus precios en `config_estancia`:
una lista de tramos `{min_horas, max_horas, precio}`. El precio de un tramo es
POR HORA: total = precio del tramo que cubre las horas * horas. Así lo calculan
el check-in (`estancias.create_estancia`), la cotización de horas extra del
checkout y el frontend (`stores/registration.ts`, `priceForChild`).

Si un producto no tiene tramos configurados (config_estancia NULL o vacío) pero
sí un `precio_unitario` mayor a cero, se usa un tramo único por hora con ese
precio, en lugar de impedir el check-in de toda la sucursal.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

# Rango del tramo de respaldo: cubre cualquier duración razonable de estancia.
_RESPALDO_MIN_HORAS = 1
_RESPALDO_MAX_HORAS = 100


def _parsear(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            valor = json.loads(raw)
        except ValueError:
            return []
        return valor if isinstance(valor, list) else []
    if isinstance(raw, list):
        return raw
    return []


def tramos_de_producto(
    config_estancia: Any, precio_unitario: Decimal | float | str | None
) -> list[dict[str, Any]]:
    """Tramos efectivos del producto de estancia, con el respaldo por precio unitario."""
    tramos = _parsear(config_estancia)
    if tramos:
        return tramos
    precio = Decimal(str(precio_unitario)) if precio_unitario is not None else Decimal("0")
    if precio > 0:
        return [
            {
                "min_horas": _RESPALDO_MIN_HORAS,
                "max_horas": _RESPALDO_MAX_HORAS,
                "precio": float(precio),
            }
        ]
    return []
