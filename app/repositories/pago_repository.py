import json
from datetime import datetime
from typing import Any
from uuid import UUID

import asyncpg

from app.schemas.pagos import PaymentItem

_INSERT = """
    INSERT INTO pagos_ordenes
        (comanda_id, metodo_pago_id, monto, notas_pago, sucursal_id, creado_por)
    VALUES ($1, $2, $3, $4, $5, $6)
    RETURNING
        id, comanda_id, metodo_pago_id, monto, notas_pago,
        sucursal_id, creado, creado_por
"""

_SELECT_HISTORIAL = """
    SELECT
        c.id                 AS comanda_id,
        c.ticket_numero,
        c.total_final,
        c.estado_actual,
        po.sucursal_id,
        MAX(po.creado)       AS creado,
        (SELECT po2.creado_por
           FROM pagos_ordenes po2
          WHERE po2.comanda_id = c.id
          LIMIT 1)            AS creado_por,
        json_agg(
            json_build_object(
                'metodo_pago_id',     po.metodo_pago_id,
                'metodo_pago_nombre', mp.nombre,
                'monto',              po.monto,
                'notas_pago',         po.notas_pago
            )
            ORDER BY po.creado
        ) AS metodos_pago
    FROM comandas c
    JOIN pagos_ordenes po ON po.comanda_id = c.id
    JOIN metodos_pago mp  ON mp.id = po.metodo_pago_id
    WHERE po.sucursal_id = $1
      AND po.creado >= $2
      AND ($3 = 'todos' OR ($3 = 'pagado' AND c.estado_actual != 'C') OR ($3 = 'cancelado' AND c.estado_actual = 'C'))
    GROUP BY c.id, c.ticket_numero, c.total_final, c.estado_actual, po.sucursal_id
    ORDER BY MAX(po.creado) DESC
"""


async def crear_pagos(
    conn: asyncpg.Connection,
    comanda_id: UUID,
    sucursal_id: UUID,
    pagos: list[PaymentItem],
    usuario_id: UUID,
) -> list[dict[str, Any]]:
    resultados: list[dict[str, Any]] = []
    for pago in pagos:
        row = await conn.fetchrow(
            _INSERT,
            comanda_id,
            pago.metodo_pago_id,
            pago.monto,
            pago.notas_pago or "",
            sucursal_id,
            usuario_id,
        )
        resultados.append(dict(row))
    return resultados


async def historial(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    desde: datetime,
    estado: str = "todos",
) -> list[dict[str, Any]]:
    rows = await conn.fetch(_SELECT_HISTORIAL, sucursal_id, desde, estado)
    resultados: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        metodos_raw = d.get("metodos_pago")
        if isinstance(metodos_raw, str):
            d["metodos_pago"] = json.loads(metodos_raw)
        elif metodos_raw is not None and not isinstance(metodos_raw, list):
            d["metodos_pago"] = list(metodos_raw)
        d["creado"] = d["creado"]
        resultados.append(d)
    return resultados


_SELECT_DETALLE_COMANDA = """
    SELECT
        c.id               AS comanda_id,
        c.ticket_numero,
        c.total_final,
        c.estado_actual,
        c.fecha_hora,
        u.nombre_completo  AS creado_por_nombre
    FROM comandas c
    LEFT JOIN usuarios u ON u.id = c.creado_por
    WHERE c.id = $1
"""

_SELECT_DETALLE_PAGOS = """
    SELECT
        mp.nombre  AS metodo_pago_nombre,
        po.monto,
        po.notas_pago
    FROM pagos_ordenes po
    JOIN metodos_pago mp ON mp.id = po.metodo_pago_id
    WHERE po.comanda_id = $1
"""

_SELECT_DETALLE_PRODUCTOS = """
    SELECT
        dc.cantidad,
        dc.precio_unitario,
        dc.importe,
        dc.notas_especiales,
        dc.nombre_combo_padre,
        p.nombre AS producto_nombre
    FROM detalles_comanda dc
    LEFT JOIN productos p ON p.id = dc.producto_id
    WHERE dc.comanda_id = $1
"""


async def detalle_por_comanda(
    conn: asyncpg.Connection,
    comanda_id: UUID,
) -> dict[str, Any] | None:
    comanda_row = await conn.fetchrow(_SELECT_DETALLE_COMANDA, comanda_id)
    if not comanda_row:
        return None

    pagos_rows = await conn.fetch(_SELECT_DETALLE_PAGOS, comanda_id)
    productos_rows = await conn.fetch(_SELECT_DETALLE_PRODUCTOS, comanda_id)

    c = dict(comanda_row)
    metodos_pago = [
        {
            "metodo_pago_nombre": dict(p)["metodo_pago_nombre"],
            "monto": float(dict(p)["monto"]),
            "notas_pago": dict(p)["notas_pago"],
        }
        for p in pagos_rows
    ]
    detalles = [
        {
            "producto_nombre": dict(row)["producto_nombre"],
            "cantidad": dict(row)["cantidad"],
            "precio_unitario": float(dict(row)["precio_unitario"]),
            "importe": float(dict(row)["importe"]),
            "notas_especiales": dict(row)["notas_especiales"],
            "nombre_combo_padre": dict(row)["nombre_combo_padre"],
        }
        for row in productos_rows
    ]

    return {
        "comanda_id": str(c["comanda_id"]),
        "ticket_numero": c["ticket_numero"],
        "total_final": float(c["total_final"]),
        "estado_actual": c["estado_actual"],
        "fecha_hora": c["fecha_hora"].isoformat() if c["fecha_hora"] else None,
        "creado_por_nombre": c["creado_por_nombre"],
        "metodos_pago": metodos_pago,
        "detalles": detalles,
    }


_SELECT_ESTADISTICAS = """
    SELECT
        COALESCE(SUM(po.monto), 0)::float   AS total_ventas,
        COUNT(DISTINCT po.comanda_id)::int   AS total_ordenes
    FROM pagos_ordenes po
    WHERE po.sucursal_id = $1
      AND po.creado >= $2
"""


async def estadisticas(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    desde: datetime,
) -> dict[str, Any]:
    row = await conn.fetchrow(_SELECT_ESTADISTICAS, sucursal_id, desde)
    return dict(row) if row else {"total_ventas": 0.0, "total_ordenes": 0}
