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
        po.id,
        po.comanda_id,
        c.ticket_numero,
        c.total_final,
        c.estado_actual,
        po.metodo_pago_id,
        mp.nombre  AS metodo_pago_nombre,
        po.monto,
        po.notas_pago,
        po.sucursal_id,
        po.creado,
        po.creado_por
    FROM pagos_ordenes po
    JOIN comandas     c  ON c.id = po.comanda_id
    JOIN metodos_pago mp ON mp.id = po.metodo_pago_id
    WHERE po.sucursal_id = $1
      AND po.creado >= $2
      AND ($3 = 'todos' OR ($3 = 'pagado' AND c.estado_actual != 'C') OR ($3 = 'cancelado' AND c.estado_actual = 'C'))
    ORDER BY po.creado DESC
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
    return [dict(r) for r in rows]


_SELECT_DETALLE = """
    SELECT
        po.id              AS pago_id,
        po.monto           AS pago_monto,
        po.notas_pago      AS pago_notas,
        po.creado          AS pago_creado,
        c.id               AS comanda_id,
        c.ticket_numero,
        c.total_final,
        c.estado_actual,
        c.fecha_hora,
        mp.nombre          AS metodo_pago_nombre,
        u.nombre_completo  AS creado_por_nombre,
        dc.id              AS detalle_id,
        dc.producto_id,
        dc.cantidad,
        dc.precio_unitario,
        dc.importe,
        dc.notas_especiales,
        dc.nombre_combo_padre,
        p.nombre           AS producto_nombre
    FROM pagos_ordenes po
    JOIN comandas       c  ON c.id  = po.comanda_id
    JOIN metodos_pago   mp ON mp.id = po.metodo_pago_id
    LEFT JOIN usuarios  u  ON u.id  = po.creado_por
    LEFT JOIN detalles_comanda dc ON dc.comanda_id = c.id
    LEFT JOIN productos        p  ON p.id = dc.producto_id
    WHERE po.id = $1
"""


async def detalle_por_id(
    conn: asyncpg.Connection,
    pago_id: UUID,
) -> dict[str, Any] | None:
    rows = await conn.fetch(_SELECT_DETALLE, pago_id)
    if not rows:
        return None

    first = dict(rows[0])
    detalles: list[dict[str, Any]] = []
    for row in rows:
        if row["detalle_id"] is not None:
            detalles.append({
                "producto_nombre": row["producto_nombre"],
                "cantidad": row["cantidad"],
                "precio_unitario": float(row["precio_unitario"]),
                "importe": float(row["importe"]),
                "notas_especiales": row.get("notas_especiales"),
                "nombre_combo_padre": row.get("nombre_combo_padre"),
            })

    return {
        "pago_id": str(first["pago_id"]),
        "pago_monto": float(first["pago_monto"]),
        "pago_notas": first["pago_notas"],
        "pago_creado": first["pago_creado"].isoformat() if first["pago_creado"] else None,
        "ticket_numero": first["ticket_numero"],
        "total_final": float(first["total_final"]),
        "estado_actual": first["estado_actual"],
        "fecha_hora": first["fecha_hora"].isoformat() if first["fecha_hora"] else None,
        "metodo_pago_nombre": first["metodo_pago_nombre"],
        "creado_por_nombre": first["creado_por_nombre"],
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
