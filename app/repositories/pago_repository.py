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

_UNION_VENTAS = """
    SELECT
        v.referencia_id,
        v.tipo_origen,
        v.titulo,
        v.estado_actual,
        v.sucursal_id,
        v.es_cancelado,
        v.monto,
        v.metodo_pago_id,
        v.metodo_pago_nombre,
        v.notas_pago,
        v.creado,
        v.creado_por
    FROM (
        -- Ventas POS (comandas)
        SELECT
            c.id                               AS referencia_id,
            'comanda'                          AS tipo_origen,
            c.ticket_numero                    AS titulo,
            c.estado_actual::text              AS estado_actual,
            po.sucursal_id                     AS sucursal_id,
            (c.estado_actual = 'C')            AS es_cancelado,
            po.monto                           AS monto,
            po.metodo_pago_id                  AS metodo_pago_id,
            mp.nombre                          AS metodo_pago_nombre,
            po.notas_pago                      AS notas_pago,
            po.creado                          AS creado,
            po.creado_por                      AS creado_por
        FROM pagos_ordenes po
        JOIN comandas c ON c.id = po.comanda_id
        JOIN metodos_pago mp ON mp.id = po.metodo_pago_id

        UNION ALL

        -- Estancias / entradas de niños
        SELECT
            r.id                               AS referencia_id,
            'estancia'                         AS tipo_origen,
            t.nombre_completo                  AS titulo,
            r.estado::text                     AS estado_actual,
            pe.sucursal_id                     AS sucursal_id,
            FALSE                              AS es_cancelado,
            pe.monto                           AS monto,
            pe.metodos_pago_id                 AS metodo_pago_id,
            mp.nombre                          AS metodo_pago_nombre,
            NULL                               AS notas_pago,
            pe.creado                          AS creado,
            pe.creado_por                      AS creado_por
        FROM pagos_estancia pe
        JOIN registros r ON r.id = pe.registros_id
        JOIN tutores t ON t.id = r.tutores_id
        JOIN metodos_pago mp ON mp.id = pe.metodos_pago_id

        UNION ALL

        -- Reservaciones / eventos
        SELECT
            r.id                               AS referencia_id,
            'reservacion'                      AS tipo_origen,
            CONCAT_WS(' ', r.nombre_cliente, r.apellidos_cliente) AS titulo,
            r.estado::text                         AS estado_actual,
            r.sucursal_id                      AS sucursal_id,
            (r.estado = 'cancelada')           AS es_cancelado,
            pr.monto                           AS monto,
            pr.metodo_pago_id                  AS metodo_pago_id,
            mp.nombre                          AS metodo_pago_nombre,
            pr.notas                           AS notas_pago,
            pr.fecha_pago                      AS creado,
            pr.creado_por                      AS creado_por
        FROM pagos_reservacion pr
        JOIN reservaciones r ON r.id = pr.reservacion_id
        JOIN metodos_pago mp ON mp.id = pr.metodo_pago_id
    ) v
"""

_SELECT_HISTORIAL = f"""
    SELECT
        v.referencia_id,
        v.tipo_origen,
        v.titulo,
        SUM(v.monto)                         AS total_final,
        v.estado_actual,
        v.sucursal_id,
        MAX(v.creado)                        AS creado,
        (ARRAY_AGG(v.creado_por) FILTER (WHERE v.creado_por IS NOT NULL))[1] AS creado_por,
        CASE WHEN v.tipo_origen = 'comanda' THEN v.referencia_id END AS comanda_id,
        CASE WHEN v.tipo_origen = 'comanda' THEN v.titulo      END AS ticket_numero,
        json_agg(
            json_build_object(
                'metodo_pago_id',     v.metodo_pago_id,
                'metodo_pago_nombre', v.metodo_pago_nombre,
                'monto',              v.monto,
                'notas_pago',         v.notas_pago
            )
            ORDER BY v.creado
        ) AS metodos_pago
    FROM ({_UNION_VENTAS}) v
    WHERE v.sucursal_id = $1
      AND v.creado >= $2::timestamptz
      AND ($3::timestamptz IS NULL OR v.creado <= $3::timestamptz)
    GROUP BY
        v.referencia_id, v.tipo_origen, v.titulo, v.estado_actual, v.sucursal_id
    HAVING (
        $4 = 'todos'
        OR ($4 = 'pagado' AND NOT bool_or(v.es_cancelado))
        OR ($4 = 'cancelado' AND bool_or(v.es_cancelado))
    )
    ORDER BY MAX(v.creado) DESC
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
        c.nombre_cliente,
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
        "tipo_origen": "comanda",
        "referencia_id": str(c["comanda_id"]),
        "titulo": c["ticket_numero"],
        "comanda_id": str(c["comanda_id"]),
        "ticket_numero": c["ticket_numero"],
        "total_final": float(c["total_final"]),
        "estado_actual": c["estado_actual"],
        "fecha_hora": c["fecha_hora"].isoformat() if c["fecha_hora"] else None,
        "motivo_cancelacion": c.get("motivo_cancelacion"),
        "creado_por_nombre": c["creado_por_nombre"],
        "nombre_cliente": c.get("nombre_cliente"),
        "metodos_pago": metodos_pago,
        "detalles": detalles,
    }


_SELECT_DETALLE_ESTANCIA = """
    SELECT
        r.id                  AS referencia_id,
        t.nombre_completo     AS titulo,
        r.total               AS total_final,
        r.estado              AS estado_actual,
        r.creado              AS fecha_hora,
        u.nombre_completo     AS creado_por_nombre
    FROM registros r
    JOIN tutores t ON t.id = r.tutores_id
    LEFT JOIN usuarios u ON u.id = r.creado_por
    WHERE r.id = $1
"""

_SELECT_DETALLE_PAGOS_ESTANCIA = """
    SELECT
        mp.nombre   AS metodo_pago_nombre,
        pe.monto,
        NULL::text  AS notas_pago
    FROM pagos_estancia pe
    JOIN metodos_pago mp ON mp.id = pe.metodos_pago_id
    WHERE pe.registros_id = $1
"""

_SELECT_DETALLE_ITEMS_ESTANCIA = """
    SELECT
        dr.id,
        p.nombre                  AS producto_nombre,
        dr.cantidad,
        dr.precio                 AS precio_unitario,
        (dr.cantidad * dr.precio) AS importe,
        n.nombre_completo         AS notas_especiales,
        NULL::text                AS nombre_combo_padre
    FROM detalles_registro dr
    JOIN productos p ON p.id = dr.productos_id
    JOIN ninos n ON n.id = dr.ninos_id
    WHERE dr.registros_id = $1
"""

_SELECT_DETALLE_RESERVACION = """
    SELECT
        r.id                                          AS referencia_id,
        CONCAT_WS(' ', r.nombre_cliente, r.apellidos_cliente) AS titulo,
        r.precio_total                                AS total_final,
        r.estado                                      AS estado_actual,
        r.creado                                      AS fecha_hora,
        u.nombre_completo                             AS creado_por_nombre
    FROM reservaciones r
    LEFT JOIN usuarios u ON u.id = r.creado_por
    WHERE r.id = $1
"""

_SELECT_DETALLE_PAGOS_RESERVACION = """
    SELECT
        mp.nombre AS metodo_pago_nombre,
        pr.monto,
        pr.notas  AS notas_pago
    FROM pagos_reservacion pr
    JOIN metodos_pago mp ON mp.id = pr.metodo_pago_id
    WHERE pr.reservacion_id = $1
"""

_SELECT_DETALLE_ITEMS_RESERVACION = """
    SELECT
        r.id,
        CONCAT('Paquete: ', pk.nombre) AS producto_nombre,
        1                              AS cantidad,
        r.precio_base                  AS precio_unitario,
        r.precio_base                  AS importe,
        NULL::text                     AS notas_especiales,
        NULL::text                     AS nombre_combo_padre
    FROM reservaciones r
    JOIN paquetes pk ON pk.id = r.paquete_id
    WHERE r.id = $1
    UNION ALL
    SELECT
        re.id,
        e.nombre              AS producto_nombre,
        re.cantidad,
        re.precio_unitario,
        re.subtotal,
        NULL::text            AS notas_especiales,
        NULL::text            AS nombre_combo_padre
    FROM reservacion_extras re
    JOIN extras e ON e.id = re.extra_id
    WHERE re.reservacion_id = $1
    UNION ALL
    SELECT
        rp.id,
        p.nombre              AS producto_nombre,
        rp.cantidad,
        rp.precio_unitario,
        rp.subtotal,
        rp.notas              AS notas_especiales,
        NULL::text            AS nombre_combo_padre
    FROM reservacion_productos rp
    JOIN productos p ON p.id = rp.producto_id
    WHERE rp.reservacion_id = $1
"""


def _armar_metodos_pago(pagos_rows: list[asyncpg.Record]) -> list[dict[str, Any]]:
    return [
        {
            "metodo_pago_nombre": dict(p)["metodo_pago_nombre"],
            "monto": float(dict(p)["monto"]),
            "notas_pago": dict(p)["notas_pago"],
        }
        for p in pagos_rows
    ]


def _armar_detalles(items_rows: list[asyncpg.Record]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(dict(row)["id"]),
            "producto_nombre": dict(row)["producto_nombre"],
            "cantidad": dict(row)["cantidad"],
            "precio_unitario": float(dict(row)["precio_unitario"]),
            "importe": float(dict(row)["importe"]),
            "notas_especiales": dict(row)["notas_especiales"],
            "nombre_combo_padre": dict(row)["nombre_combo_padre"],
        }
        for row in items_rows
    ]


async def _detalle_estancia(
    conn: asyncpg.Connection, registro_id: UUID
) -> dict[str, Any] | None:
    row = await conn.fetchrow(_SELECT_DETALLE_ESTANCIA, registro_id)
    if not row:
        return None
    c = dict(row)
    pagos_rows = await conn.fetch(_SELECT_DETALLE_PAGOS_ESTANCIA, registro_id)
    items_rows = await conn.fetch(_SELECT_DETALLE_ITEMS_ESTANCIA, registro_id)
    return {
        "tipo_origen": "estancia",
        "referencia_id": str(c["referencia_id"]),
        "titulo": c["titulo"],
        "comanda_id": None,
        "ticket_numero": None,
        "total_final": float(c["total_final"]),
        "estado_actual": c["estado_actual"],
        "fecha_hora": c["fecha_hora"].isoformat() if c["fecha_hora"] else None,
        "motivo_cancelacion": None,
        "creado_por_nombre": c["creado_por_nombre"],
        "metodos_pago": _armar_metodos_pago(pagos_rows),
        "detalles": _armar_detalles(items_rows),
    }


async def _detalle_reservacion(
    conn: asyncpg.Connection, reservacion_id: UUID
) -> dict[str, Any] | None:
    row = await conn.fetchrow(_SELECT_DETALLE_RESERVACION, reservacion_id)
    if not row:
        return None
    c = dict(row)
    pagos_rows = await conn.fetch(_SELECT_DETALLE_PAGOS_RESERVACION, reservacion_id)
    items_rows = await conn.fetch(_SELECT_DETALLE_ITEMS_RESERVACION, reservacion_id)
    return {
        "tipo_origen": "reservacion",
        "referencia_id": str(c["referencia_id"]),
        "titulo": c["titulo"],
        "comanda_id": None,
        "ticket_numero": None,
        "total_final": float(c["total_final"]),
        "estado_actual": c["estado_actual"],
        "fecha_hora": c["fecha_hora"].isoformat() if c["fecha_hora"] else None,
        "motivo_cancelacion": None,
        "creado_por_nombre": c["creado_por_nombre"],
        "metodos_pago": _armar_metodos_pago(pagos_rows),
        "detalles": _armar_detalles(items_rows),
    }


async def detalle_por_referencia(
    conn: asyncpg.Connection,
    tipo_origen: str,
    referencia_id: UUID,
) -> dict[str, Any] | None:
    if tipo_origen == "estancia":
        return await _detalle_estancia(conn, referencia_id)
    if tipo_origen == "reservacion":
        return await _detalle_reservacion(conn, referencia_id)
    return await detalle_por_comanda(conn, referencia_id)


_SELECT_ESTADISTICAS = f"""
    SELECT
        COALESCE(SUM(v.monto), 0)::float     AS total_ventas,
        COUNT(DISTINCT v.referencia_id)::int  AS total_ordenes
    FROM ({_UNION_VENTAS}) v
    WHERE v.sucursal_id = $1
      AND v.creado >= $2::timestamptz
      AND ($3::timestamptz IS NULL OR v.creado <= $3::timestamptz)
      AND NOT v.es_cancelado
"""


async def estadisticas(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    desde: datetime,
    hasta: datetime | None = None,
) -> dict[str, Any]:
    row = await conn.fetchrow(_SELECT_ESTADISTICAS, sucursal_id, desde, hasta)
    return dict(row) if row else {"total_ventas": 0.0, "total_ordenes": 0}
