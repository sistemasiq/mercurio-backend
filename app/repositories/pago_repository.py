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

# El historial es la vista de "todo el dinero que entró", así que une dos orígenes:
# las ventas de mostrador (comandas) y los cobros de eventos (pagos_reservacion),
# que antes no aparecían por ningún lado aunque sí afectan la caja.
#
# Los dos lados agrupan distinto a propósito:
#   - Una comanda es UN renglón con todos sus pagos agregados: se cobra de una vez,
#     posiblemente repartida entre métodos.
#   - Una reservación es UN renglón POR PAGO, porque su anticipo y su liquidación
#     ocurren en fechas distintas y son ingresos separados. Colapsarlos por
#     reservación haría que un anticipo de julio se contara dentro de agosto.
_SELECT_HISTORIAL = """
    WITH ordenes AS (
        SELECT
            c.id                 AS comanda_id,
            -- ticket_numero y estado_actual se castean a text porque del lado de
            -- comandas son varchar y un ENUM (estado_comanda), y UNION exige que
            -- ambas ramas coincidan exactamente en tipo.
            c.ticket_numero::text AS ticket_numero,
            c.total_final,
            c.estado_actual::text AS estado_actual,
            po.sucursal_id,
            MAX(po.creado)       AS creado,
            (SELECT po2.creado_por
               FROM pagos_ordenes po2
              WHERE po2.comanda_id = c.id
              LIMIT 1)            AS creado_por,
            'orden'              AS origen,
            NULL::text           AS concepto,
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
          AND po.creado >= $2::timestamptz
          AND ($3::timestamptz IS NULL OR po.creado <= $3::timestamptz)
          AND (
              $4 = 'todos'
              OR ($4 = 'pagado' AND c.estado_actual != 'C')
              OR ($4 = 'cancelado' AND c.estado_actual = 'C')
          )
        GROUP BY c.id, c.ticket_numero, c.total_final, c.estado_actual, po.sucursal_id
    ),
    eventos AS (
        SELECT
            pr.id                AS comanda_id,
            -- Las reservaciones no tienen folio propio; se identifica al evento por
            -- su cliente, que es como el staff lo reconoce en la agenda.
            COALESCE(NULLIF(TRIM(r.nombre_cliente), ''), 'Evento')::text AS ticket_numero,
            pr.monto             AS total_final,
            -- Ninguna reservación se cancela hoy (estados: pendiente/confirmada/
            -- completada), pero se mapea igual para que el filtro 'cancelado' del
            -- historial siga teniendo un significado único entre ambos orígenes.
            (CASE WHEN r.estado = 'cancelada' THEN 'C' ELSE 'P' END)::text AS estado_actual,
            r.sucursal_id,
            pr.fecha_pago        AS creado,
            pr.creado_por,
            'evento'             AS origen,
            pr.notas             AS concepto,
            json_build_array(
                json_build_object(
                    'metodo_pago_id',     pr.metodo_pago_id,
                    'metodo_pago_nombre', mp.nombre,
                    'monto',              pr.monto,
                    'notas_pago',         pr.notas
                )
            ) AS metodos_pago
        FROM pagos_reservacion pr
        JOIN reservaciones r  ON r.id = pr.reservacion_id
        JOIN metodos_pago mp  ON mp.id = pr.metodo_pago_id
        WHERE r.sucursal_id = $1
          AND pr.fecha_pago >= $2::timestamptz
          AND ($3::timestamptz IS NULL OR pr.fecha_pago <= $3::timestamptz)
          AND (
              $4 = 'todos'
              OR ($4 = 'pagado' AND r.estado <> 'cancelada')
              OR ($4 = 'cancelado' AND r.estado = 'cancelada')
          )
    )
    SELECT * FROM ordenes
    UNION ALL
    SELECT * FROM eventos
    ORDER BY creado DESC
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
    hasta: datetime | None = None,
) -> list[dict[str, Any]]:
    rows = await conn.fetch(_SELECT_HISTORIAL, sucursal_id, desde, hasta, estado)
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
        c.motivo_cancelacion,
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
        dc.id,
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
            "id": str(dict(row)["id"]),
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
        "motivo_cancelacion": c.get("motivo_cancelacion"),
        "creado_por_nombre": c["creado_por_nombre"],
        "metodos_pago": metodos_pago,
        "detalles": detalles,
    }


# Mismo criterio que _SELECT_HISTORIAL: el total es el ingreso del periodo, sumando
# mostrador y eventos. Se cuenta una orden por comanda y un movimiento por cobro de
# evento, que es la unidad en que cada uno entra a caja.
_SELECT_ESTADISTICAS = """
    SELECT
        (
            SELECT COALESCE(SUM(po.monto), 0)
            FROM pagos_ordenes po
            JOIN comandas c ON c.id = po.comanda_id
            WHERE po.sucursal_id = $1
              AND po.creado >= $2::timestamptz
              AND ($3::timestamptz IS NULL OR po.creado <= $3::timestamptz)
              AND c.estado_actual != 'C'
        )
        +
        (
            SELECT COALESCE(SUM(pr.monto), 0)
            FROM pagos_reservacion pr
            JOIN reservaciones r ON r.id = pr.reservacion_id
            WHERE r.sucursal_id = $1
              AND pr.fecha_pago >= $2::timestamptz
              AND ($3::timestamptz IS NULL OR pr.fecha_pago <= $3::timestamptz)
              AND r.estado <> 'cancelada'
        ) AS total_ventas_num,
        (
            SELECT COUNT(DISTINCT po.comanda_id)
            FROM pagos_ordenes po
            JOIN comandas c ON c.id = po.comanda_id
            WHERE po.sucursal_id = $1
              AND po.creado >= $2::timestamptz
              AND ($3::timestamptz IS NULL OR po.creado <= $3::timestamptz)
              AND c.estado_actual != 'C'
        )
        +
        (
            SELECT COUNT(*)
            FROM pagos_reservacion pr
            JOIN reservaciones r ON r.id = pr.reservacion_id
            WHERE r.sucursal_id = $1
              AND pr.fecha_pago >= $2::timestamptz
              AND ($3::timestamptz IS NULL OR pr.fecha_pago <= $3::timestamptz)
              AND r.estado <> 'cancelada'
        ) AS total_ordenes_num
"""


async def estadisticas(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    desde: datetime,
    hasta: datetime | None = None,
) -> dict[str, Any]:
    row = await conn.fetchrow(_SELECT_ESTADISTICAS, sucursal_id, desde, hasta)
    if row is None:
        return {"total_ventas": 0.0, "total_ordenes": 0}
    # Los subselects devuelven numeric/bigint; se normaliza aquí para que el
    # servicio siga recibiendo los mismos tipos que antes de unir los dos orígenes.
    return {
        "total_ventas": float(row["total_ventas_num"] or 0),
        "total_ordenes": int(row["total_ordenes_num"] or 0),
    }
