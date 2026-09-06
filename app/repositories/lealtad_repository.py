from datetime import date, datetime
from typing import Any
from uuid import UUID

import asyncpg

_SELECT = """
    SELECT sucursal_id, porcentaje_retorno, dias_caducidad, valor_punto, activo,
           otorga_puntos_comandas, otorga_puntos_reservaciones, otorga_puntos_checkin,
           creado, creado_por, modificado, modificado_por
    FROM configuracion_lealtad
"""


async def obtener_configuracion(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> dict[str, Any] | None:
    row = await conn.fetchrow(_SELECT + " WHERE sucursal_id = $1", sucursal_id)
    return dict(row) if row else None


async def upsert_configuracion(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    porcentaje_retorno: float,
    dias_caducidad: int,
    valor_punto: float,
    activo: bool,
    usuario_id: UUID,
    otorga_puntos_comandas: bool = True,
    otorga_puntos_reservaciones: bool = True,
    otorga_puntos_checkin: bool = True,
) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        INSERT INTO configuracion_lealtad
            (sucursal_id, porcentaje_retorno, dias_caducidad, valor_punto,
             activo, otorga_puntos_comandas, otorga_puntos_reservaciones,
             otorga_puntos_checkin, creado_por, modificado_por)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $9)
        ON CONFLICT (sucursal_id) DO UPDATE SET
            porcentaje_retorno = EXCLUDED.porcentaje_retorno,
            dias_caducidad = EXCLUDED.dias_caducidad,
            valor_punto = EXCLUDED.valor_punto,
            activo = EXCLUDED.activo,
            otorga_puntos_comandas = EXCLUDED.otorga_puntos_comandas,
            otorga_puntos_reservaciones = EXCLUDED.otorga_puntos_reservaciones,
            otorga_puntos_checkin = EXCLUDED.otorga_puntos_checkin,
            modificado = NOW(),
            modificado_por = EXCLUDED.modificado_por
        RETURNING sucursal_id, porcentaje_retorno, dias_caducidad, valor_punto, activo,
                  otorga_puntos_comandas, otorga_puntos_reservaciones, otorga_puntos_checkin,
                  creado, creado_por, modificado, modificado_por
        """,
        sucursal_id,
        porcentaje_retorno,
        dias_caducidad,
        valor_punto,
        activo,
        otorga_puntos_comandas,
        otorga_puntos_reservaciones,
        otorga_puntos_checkin,
        usuario_id,
    )
    return dict(row)


async def crear_lote(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    celular: str,
    puntos: int,
    fecha_caducidad: datetime,
    usuario_id: UUID,
    comanda_id: UUID | None = None,
    reservacion_id: UUID | None = None,
    registro_id: UUID | None = None,
) -> dict[str, Any]:
    """Crea un lote de puntos otorgados. Exactamente una de comanda_id,
    reservacion_id o registro_id debe venir, según el origen del pago (venta
    de caja, anticipo de reservación, o check-in de niños) -- el CHECK de BD
    lo exige."""
    row = await conn.fetchrow(
        """
        INSERT INTO lotes_puntos
            (sucursal_id, celular, comanda_id, reservacion_id, registro_id,
             puntos_otorgados, puntos_disponibles, fecha_caducidad, creado_por)
        VALUES ($1, $2, $3, $4, $5, $6, $6, $7, $8)
        RETURNING id, sucursal_id, celular, comanda_id, reservacion_id, registro_id,
                  puntos_otorgados, puntos_disponibles, fecha_otorgado, fecha_caducidad,
                  creado_por
        """,
        sucursal_id,
        celular,
        comanda_id,
        reservacion_id,
        registro_id,
        puntos,
        fecha_caducidad,
        usuario_id,
    )
    return dict(row)


async def obtener_lote_por_comanda(
    conn: asyncpg.Connection, comanda_id: UUID
) -> dict[str, Any] | None:
    row = await conn.fetchrow(
        """
        SELECT id, sucursal_id, celular, comanda_id, puntos_otorgados, puntos_disponibles,
               fecha_otorgado, fecha_caducidad, creado_por
        FROM lotes_puntos
        WHERE comanda_id = $1
        """,
        comanda_id,
    )
    return dict(row) if row else None


async def anular_lote(conn: asyncpg.Connection, lote_id: UUID) -> None:
    await conn.execute("UPDATE lotes_puntos SET puntos_disponibles = 0 WHERE id = $1", lote_id)


async def lotes_vigentes_for_update(
    conn: asyncpg.Connection, sucursal_id: UUID, celular: str
) -> list[dict[str, Any]]:
    """Lotes con saldo vigente, bloqueados para actualización (FOR UPDATE) y
    ordenados por fecha de caducidad ascendente — el canje consume primero
    el lote más próximo a vencer. El lock evita que dos redenciones
    concurrentes del mismo celular sobre-consuman el mismo lote."""
    rows = await conn.fetch(
        """
        SELECT id, puntos_disponibles, fecha_caducidad
        FROM lotes_puntos
        WHERE sucursal_id = $1 AND celular = $2
          AND puntos_disponibles > 0 AND fecha_caducidad > NOW()
        ORDER BY fecha_caducidad ASC
        FOR UPDATE
        """,
        sucursal_id,
        celular,
    )
    return [dict(r) for r in rows]


async def descontar_lote(conn: asyncpg.Connection, lote_id: UUID, cantidad: int) -> None:
    await conn.execute(
        "UPDATE lotes_puntos SET puntos_disponibles = puntos_disponibles - $2 WHERE id = $1",
        lote_id,
        cantidad,
    )


async def calcular_saldo(conn: asyncpg.Connection, sucursal_id: UUID, celular: str) -> int:
    row = await conn.fetchrow(
        """
        SELECT COALESCE(SUM(puntos_disponibles), 0) AS saldo
        FROM lotes_puntos
        WHERE sucursal_id = $1 AND celular = $2 AND fecha_caducidad > NOW()
        """,
        sucursal_id,
        celular,
    )
    return int(row["saldo"]) if row else 0


async def registrar_movimiento(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    celular: str,
    lote_id: UUID | None,
    comanda_id: UUID | None,
    tipo: str,
    puntos: int,
    saldo_resultante: int,
    notas: str | None,
    usuario_id: UUID | None,
    reservacion_id: UUID | None = None,
    registro_id: UUID | None = None,
) -> None:
    await conn.execute(
        """
        INSERT INTO movimientos_puntos
            (sucursal_id, celular, lote_id, comanda_id, reservacion_id, registro_id,
             tipo, puntos, saldo_resultante, notas, creado_por)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """,
        sucursal_id,
        celular,
        lote_id,
        comanda_id,
        reservacion_id,
        registro_id,
        tipo,
        puntos,
        saldo_resultante,
        notas,
        usuario_id,
    )


async def reporte_agregado(conn: asyncpg.Connection, sucursal_id: UUID) -> dict[str, Any]:
    """KPIs agregados de todo el programa de lealtad en una sucursal (todos
    los celulares juntos). `caducado` se calcula sobre `lotes_puntos`
    porque la caducidad no se registra como movimiento (es una condición de
    lectura, no un evento escrito)."""
    row = await conn.fetchrow(
        """
        SELECT
            COALESCE((SELECT SUM(puntos) FROM movimientos_puntos
                      WHERE sucursal_id = $1 AND tipo = 'O'), 0) AS total_otorgado,
            COALESCE((SELECT SUM(-puntos) FROM movimientos_puntos
                      WHERE sucursal_id = $1 AND tipo = 'R'), 0) AS total_redimido,
            COALESCE((SELECT SUM(puntos_disponibles) FROM lotes_puntos
                      WHERE sucursal_id = $1 AND fecha_caducidad <= NOW()
                        AND puntos_disponibles > 0), 0) AS total_caducado,
            COALESCE((SELECT SUM(puntos_disponibles) FROM lotes_puntos
                      WHERE sucursal_id = $1 AND fecha_caducidad > NOW()), 0) AS saldo_vigente,
            COALESCE((SELECT COUNT(DISTINCT celular) FROM lotes_puntos
                      WHERE sucursal_id = $1 AND fecha_caducidad > NOW()
                        AND puntos_disponibles > 0), 0) AS clientes_con_saldo
        """,
        sucursal_id,
    )
    return dict(row) if row else {}


async def listar_movimientos(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    celular: str,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[dict[str, Any]]:
    """Historial de movimientos de puntos de un celular en una sucursal
    (kardex), opcionalmente acotado a un rango de fechas. `hasta` es
    inclusivo del día completo."""
    conditions = ["sucursal_id = $1", "celular = $2"]
    params: list[Any] = [sucursal_id, celular]
    if desde is not None:
        params.append(desde)
        conditions.append(f"creado >= ${len(params)}")
    if hasta is not None:
        params.append(hasta)
        conditions.append(f"creado < ${len(params)}::date + interval '1 day'")

    where_clause = " AND ".join(conditions)
    rows = await conn.fetch(
        f"""
        SELECT id, sucursal_id, celular, lote_id, comanda_id, tipo, puntos,
               saldo_resultante, notas, creado, creado_por
        FROM movimientos_puntos
        WHERE {where_clause}
        ORDER BY creado DESC
        """,
        *params,
    )
    return [dict(r) for r in rows]
