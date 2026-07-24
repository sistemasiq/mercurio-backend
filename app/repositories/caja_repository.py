"""
app/repositories/caja_repository.py
Única capa que habla con la BD para el módulo de Cierre de Caja — SQL crudo con asyncpg.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import asyncpg

from app.core.utils import get_mexico_now


# ── Catálogos: Cajas y Turnos ─────────────────────────────────────────────────

async def get_caja_por_codigo(conn: asyncpg.Connection, sucursal_id: str, codigo: str) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT id, sucursal_id, codigo, nombre, creado
        FROM public.cajas
        WHERE sucursal_id = $1 AND codigo = $2
        """,
        uuid.UUID(sucursal_id),
        codigo,
    )
    return dict(row) if row else None


async def crear_caja(
    conn: asyncpg.Connection,
    sucursal_id: str,
    codigo: str,
    nombre: str,
    creado_por: str | None = None,
) -> dict:
    caja_id = uuid.uuid4()
    now = get_mexico_now()
    row = await conn.fetchrow(
        """
        INSERT INTO public.cajas (id, sucursal_id, codigo, nombre, creado, creado_por)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, sucursal_id, codigo, nombre, creado
        """,
        caja_id,
        uuid.UUID(sucursal_id),
        codigo,
        nombre,
        now,
        uuid.UUID(creado_por) if creado_por else None,
    )
    return dict(row)


async def listar_cajas_por_sucursal(conn: asyncpg.Connection, sucursal_id: str | None = None) -> list[dict]:
    if sucursal_id and sucursal_id != "00000000-0000-0000-0000-000000000000":
        rows = await conn.fetch(
            """
            SELECT id, sucursal_id, codigo, nombre, creado
            FROM public.cajas
            WHERE sucursal_id = $1
            ORDER BY codigo ASC
            """,
            uuid.UUID(sucursal_id),
        )
        if not rows:
            await crear_caja(conn, sucursal_id, "CAJA 01", "Caja Principal 01")
            await crear_caja(conn, sucursal_id, "CAJA 02", "Caja Secundaria 02")
            rows = await conn.fetch(
                """
                SELECT id, sucursal_id, codigo, nombre, creado
                FROM public.cajas
                WHERE sucursal_id = $1
                ORDER BY codigo ASC
                """,
                uuid.UUID(sucursal_id),
            )
        return [dict(r) for r in rows]
    else:
        rows = await conn.fetch(
            """
            SELECT id, sucursal_id, codigo, nombre, creado
            FROM public.cajas
            ORDER BY codigo ASC
            """
        )
        if not rows:
            suc = await conn.fetchval("SELECT id FROM public.sucursales LIMIT 1")
            suc_str = str(suc) if suc else "00000000-0000-0000-0000-000000000000"
            await crear_caja(conn, suc_str, "CAJA 01", "Caja Principal 01")
            await crear_caja(conn, suc_str, "CAJA 02", "Caja Secundaria 02")
            rows = await conn.fetch(
                """
                SELECT id, sucursal_id, codigo, nombre, creado
                FROM public.cajas
                ORDER BY codigo ASC
                """
            )
        return [dict(r) for r in rows]


async def listar_turnos(conn: asyncpg.Connection) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT id, nombre, hora_inicio, hora_fin
        FROM public.turnos
        ORDER BY hora_inicio ASC
        """
    )
    if not rows:
        now = get_mexico_now()
        default_turnos = [
            ("Turno Matutino", "08:00:00", "16:00:00"),
            ("Turno Vespertino", "16:00:00", "00:00:00"),
            ("Turno Nocturno", "00:00:00", "08:00:00"),
        ]
        for nom, hi, hf in default_turnos:
            t_id = uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO public.turnos (id, nombre, hora_inicio, hora_fin, creado)
                VALUES ($1, $2, $3::time, $4::time, $5)
                ON CONFLICT (nombre) DO NOTHING
                """,
                t_id,
                nom,
                datetime.strptime(hi, "%H:%M:%S").time(),
                datetime.strptime(hf, "%H:%M:%S").time(),
                now,
            )
        rows = await conn.fetch(
            """
            SELECT id, nombre, hora_inicio, hora_fin
            FROM public.turnos
            ORDER BY hora_inicio ASC
            """
        )
    return [dict(r) for r in rows]


async def get_primer_turno(conn: asyncpg.Connection) -> dict | None:
    turnos = await listar_turnos(conn)
    return turnos[0] if turnos else None


# ── Apertura de Caja ──────────────────────────────────────────────────────────

async def get_apertura_activa_por_usuario(conn: asyncpg.Connection, cajero_id: str) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT
            a.id,
            a.caja_id,
            a.cajero_id,
            a.turno_id,
            a.fondo_inicial,
            a.estado,
            a.conteo_json,
            a.monto_declarado,
            a.token_admin_jti,
            a.creado AS fecha_apertura,
            c.nombre AS caja_nombre,
            c.codigo AS terminal,
            c.sucursal_id,
            COALESCE(s.nombre, 'Sucursal Central') AS sucursal_nombre,
            COALESCE(u.nombre_completo, u.email, 'Cajero') AS cajero_nombre
        FROM public.apertura_caja a
        INNER JOIN public.cajas c ON a.caja_id = c.id
        LEFT JOIN public.sucursales s ON c.sucursal_id = s.id
        LEFT JOIN public.usuarios u ON a.cajero_id = u.id
        WHERE a.cajero_id = $1 AND a.estado IN ('ABIERTA', 'EN_CORTE')
        ORDER BY a.creado DESC
        LIMIT 1
        """,
        uuid.UUID(cajero_id),
    )
    return dict(row) if row else None


async def get_apertura_activa_por_caja(conn: asyncpg.Connection, caja_id: str) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT
            a.id,
            a.caja_id,
            a.cajero_id,
            a.turno_id,
            a.fondo_inicial,
            a.estado,
            a.creado AS fecha_apertura
        FROM public.apertura_caja a
        WHERE a.caja_id = $1 AND a.estado IN ('ABIERTA', 'EN_CORTE')
        LIMIT 1
        """,
        uuid.UUID(caja_id),
    )
    return dict(row) if row else None


async def get_apertura_por_id(conn: asyncpg.Connection, apertura_id: str) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT
            a.id,
            a.caja_id,
            a.cajero_id,
            a.turno_id,
            a.fondo_inicial,
            a.estado,
            a.conteo_json,
            a.monto_declarado,
            a.token_admin_jti,
            a.creado AS fecha_apertura,
            c.nombre AS caja_nombre,
            c.codigo AS terminal,
            c.sucursal_id,
            COALESCE(s.nombre, 'Sucursal Central') AS sucursal_nombre,
            COALESCE(u.nombre_completo, u.email, 'Cajero') AS cajero_nombre
        FROM public.apertura_caja a
        INNER JOIN public.cajas c ON a.caja_id = c.id
        LEFT JOIN public.sucursales s ON c.sucursal_id = s.id
        LEFT JOIN public.usuarios u ON a.cajero_id = u.id
        WHERE a.id = $1
        """,
        uuid.UUID(apertura_id),
    )
    return dict(row) if row else None


async def crear_apertura_caja(
    conn: asyncpg.Connection,
    caja_id: str,
    cajero_id: str,
    turno_id: str,
    fondo_inicial: Decimal,
    creado_por: str | None = None,
) -> dict:
    apertura_id = uuid.uuid4()
    now = get_mexico_now()
    user_uuid = uuid.UUID(cajero_id)
    await conn.execute(
        """
        INSERT INTO public.apertura_caja
            (id, caja_id, cajero_id, turno_id, fondo_inicial, estado, creado, creado_por)
        VALUES ($1, $2, $3, $4, $5, 'ABIERTA', $6, $7)
        """,
        apertura_id,
        uuid.UUID(caja_id),
        user_uuid,
        uuid.UUID(turno_id),
        fondo_inicial,
        now,
        uuid.UUID(creado_por) if creado_por else user_uuid,
    )
    res = await get_apertura_por_id(conn, str(apertura_id))
    assert res is not None
    return res


async def actualizar_estado_apertura(conn: asyncpg.Connection, apertura_id: str, nuevo_estado: str) -> None:
    now = get_mexico_now()
    await conn.execute(
        """
        UPDATE public.apertura_caja
        SET estado = $1, modificado = $2
        WHERE id = $3
        """,
        nuevo_estado,
        now,
        uuid.UUID(apertura_id),
    )


async def guardar_conteo(
    conn: asyncpg.Connection,
    apertura_id: str,
    conteo_json: str,
    monto_declarado: Decimal,
) -> None:
    now = get_mexico_now()
    await conn.execute(
        """
        UPDATE public.apertura_caja
        SET conteo_json = $1, monto_declarado = $2, modificado = $3
        WHERE id = $4
        """,
        conteo_json,
        monto_declarado,
        now,
        uuid.UUID(apertura_id),
    )


async def guardar_token_admin(conn: asyncpg.Connection, apertura_id: str, jti: uuid.UUID) -> None:
    now = get_mexico_now()
    await conn.execute(
        """
        UPDATE public.apertura_caja
        SET token_admin_jti = $1, modificado = $2
        WHERE id = $3
        """,
        jti,
        now,
        uuid.UUID(apertura_id),
    )


async def verificar_token_admin(conn: asyncpg.Connection, apertura_id: str) -> uuid.UUID | None:
    return await conn.fetchval(
        "SELECT token_admin_jti FROM public.apertura_caja WHERE id = $1",
        uuid.UUID(apertura_id),
    )


async def invalidar_token_admin(conn: asyncpg.Connection, apertura_id: str) -> None:
    now = get_mexico_now()
    await conn.execute(
        """
        UPDATE public.apertura_caja
        SET token_admin_jti = NULL, modificado = $1
        WHERE id = $2
        """,
        now,
        uuid.UUID(apertura_id),
    )


# ── Retiros Parciales ─────────────────────────────────────────────────────────

async def crear_retiro_parcial(
    conn: asyncpg.Connection,
    apertura_caja_id: str,
    concepto: str,
    tipo_destinatario: str,
    monto: Decimal,
    observaciones: str | None = None,
    creado_por: str | None = None,
) -> dict:
    now = get_mexico_now()
    row = await conn.fetchrow(
        """
        INSERT INTO public.retiros_parciales
            (apertura_caja_id, concepto, tipo_destinatario, monto, observaciones, creado, creado_por)
        VALUES ($1, $2::conceptos_retiro, $3::tipos_destinatario, $4, $5, $6, $7)
        RETURNING id, apertura_caja_id, concepto, tipo_destinatario, monto, observaciones, creado
        """,
        uuid.UUID(apertura_caja_id),
        concepto,
        tipo_destinatario,
        monto,
        observaciones,
        now,
        uuid.UUID(creado_por) if creado_por else None,
    )
    return dict(row)


async def sumar_retiros_por_apertura(conn: asyncpg.Connection, apertura_caja_id: str) -> Decimal:
    val = await conn.fetchval(
        """
        SELECT COALESCE(SUM(monto), 0)
        FROM public.retiros_parciales
        WHERE apertura_caja_id = $1
        """,
        uuid.UUID(apertura_caja_id),
    )
    return Decimal(str(val))


async def listar_retiros_por_apertura(conn: asyncpg.Connection, apertura_caja_id: str) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT id, apertura_caja_id, concepto, tipo_destinatario, monto, observaciones, creado
        FROM public.retiros_parciales
        WHERE apertura_caja_id = $1
        ORDER BY creado DESC
        """,
        uuid.UUID(apertura_caja_id),
    )
    return [dict(r) for r in rows]


# ── Movimientos de Caja ───────────────────────────────────────────────────────

async def registrar_movimiento_caja(
    conn: asyncpg.Connection,
    apertura_caja_id: str,
    tipo_movimiento: str,
    referencia_id: str,
    metodo_pago_id: str,
    monto: Decimal,
    creado_por: str | None = None,
) -> dict:
    now = get_mexico_now()
    row = await conn.fetchrow(
        """
        INSERT INTO public.movimientos_caja
            (apertura_caja_id, tipo_movimiento, referencia_id, metodo_pago_id, monto, creado, creado_por)
        VALUES ($1, $2::tipo_movimiento_caja, $3, $4, $5, $6, $7)
        RETURNING id, apertura_caja_id, tipo_movimiento, referencia_id, metodo_pago_id, monto, creado
        """,
        uuid.UUID(apertura_caja_id),
        tipo_movimiento,
        uuid.UUID(referencia_id),
        uuid.UUID(metodo_pago_id),
        monto,
        now,
        uuid.UUID(creado_por) if creado_por else None,
    )
    return dict(row)


async def obtener_movimientos_por_metodo(conn: asyncpg.Connection, apertura_caja_id: str) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT
            m.metodo_pago_id,
            mp.nombre AS metodo_nombre,
            COALESCE(SUM(m.monto), 0) AS total_ventas
        FROM public.movimientos_caja m
        INNER JOIN public.metodos_pago mp ON m.metodo_pago_id = mp.id
        WHERE m.apertura_caja_id = $1
        GROUP BY m.metodo_pago_id, mp.nombre
        """,
        uuid.UUID(apertura_caja_id),
    )
    return [dict(r) for r in rows]


async def obtener_metodos_con_movimientos(conn: asyncpg.Connection, apertura_caja_id: str) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT DISTINCT mp.id, mp.nombre
        FROM public.movimientos_caja m
        INNER JOIN public.metodos_pago mp ON m.metodo_pago_id = mp.id
        WHERE m.apertura_caja_id = $1
        ORDER BY mp.nombre ASC
        """,
        uuid.UUID(apertura_caja_id),
    )
    return [dict(r) for r in rows]


async def sumar_total_ventas_apertura(conn: asyncpg.Connection, apertura_caja_id: str) -> Decimal:
    val = await conn.fetchval(
        """
        SELECT COALESCE(SUM(monto), 0)
        FROM public.movimientos_caja
        WHERE apertura_caja_id = $1
        """,
        uuid.UUID(apertura_caja_id),
    )
    return Decimal(str(val))


# ── Cierre de Caja ────────────────────────────────────────────────────────────

async def crear_cierre_caja(
    conn: asyncpg.Connection,
    apertura_caja_id: str,
    tipo_cierre: str,
    monto_sistema: Decimal,
    monto_cierre: Decimal,
    cajero_id: str | None,
    administrador_id: str,
    observaciones: str | None = None,
    creado_por: str | None = None,
) -> dict:
    cierre_id = uuid.uuid4()
    now = get_mexico_now()
    row = await conn.fetchrow(
        """
        INSERT INTO public.cierre_caja (
            id,
            apertura_caja_id,
            tipo_cierre,
            monto_sistema,
            monto_cierre,
            cajero_id,
            fecha_autorizacion_cajero,
            administrador_id,
            fecha_autorizacion_admin,
            observaciones,
            creado,
            creado_por
        ) VALUES (
            $1, $2, $3::tipo_cierre_enum, $4, $5, $6, $7, $8, $9, $10, $11, $12
        )
        RETURNING id, apertura_caja_id, tipo_cierre, monto_sistema, monto_cierre, creado
        """,
        cierre_id,
        uuid.UUID(apertura_caja_id),
        tipo_cierre,
        monto_sistema,
        monto_cierre,
        uuid.UUID(cajero_id) if cajero_id else None,
        now if cajero_id else None,
        uuid.UUID(administrador_id),
        now,
        observaciones,
        now,
        uuid.UUID(creado_por) if creado_por else uuid.UUID(administrador_id),
    )
    return dict(row)


async def listar_historial_cierres(
    conn: asyncpg.Connection,
    sucursal_id: str | None = None,
    cajero_id: str | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    offset: int = 0,
    limit: int = 20,
) -> list[dict]:
    query = """
        SELECT
            cc.id,
            a.creado AS fecha_apertura,
            cc.fecha_autorizacion_admin AS fecha_cierre,
            a.fondo_inicial,
            cc.monto_cierre AS total_declarado,
            cc.monto_sistema AS total_esperado,
            (cc.monto_cierre - cc.monto_sistema) AS diferencia_neta,
            c.codigo AS terminal,
            COALESCE(s.nombre, 'Sucursal Central') AS sucursal_nombre,
            COALESCE(u_cajero.nombre_completo, u_cajero.email, 'Cajero') AS cajero_nombre,
            COALESCE(u_admin.nombre_completo, u_admin.email, 'Administrador') AS admin_nombre,
            (cc.observaciones IS NOT NULL AND cc.observaciones <> '') AS tiene_observaciones
        FROM public.cierre_caja cc
        INNER JOIN public.apertura_caja a ON cc.apertura_caja_id = a.id
        INNER JOIN public.cajas c ON a.caja_id = c.id
        LEFT JOIN public.sucursales s ON c.sucursal_id = s.id
        LEFT JOIN public.usuarios u_cajero ON cc.cajero_id = u_cajero.id
        LEFT JOIN public.usuarios u_admin ON cc.administrador_id = u_admin.id
        WHERE 1=1
    """
    params: list[Any] = []
    param_idx = 1

    if sucursal_id:
        query += f" AND c.sucursal_id = ${param_idx}"
        params.append(uuid.UUID(sucursal_id))
        param_idx += 1

    if cajero_id:
        query += f" AND a.cajero_id = ${param_idx}"
        params.append(uuid.UUID(cajero_id))
        param_idx += 1

    if fecha_desde:
        query += f" AND cc.fecha_autorizacion_admin >= ${param_idx}"
        params.append(fecha_desde)
        param_idx += 1

    if fecha_hasta:
        query += f" AND cc.fecha_autorizacion_admin <= ${param_idx}"
        params.append(fecha_hasta)
        param_idx += 1

    query += f" ORDER BY cc.fecha_autorizacion_admin DESC OFFSET ${param_idx} LIMIT ${param_idx + 1}"
    params.extend([offset, limit])

    rows = await conn.fetch(query, *params)
    return [dict(r) for r in rows]


async def contar_historial_cierres(
    conn: asyncpg.Connection,
    sucursal_id: str | None = None,
    cajero_id: str | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
) -> int:
    query = """
        SELECT COUNT(*)
        FROM public.cierre_caja cc
        INNER JOIN public.apertura_caja a ON cc.apertura_caja_id = a.id
        INNER JOIN public.cajas c ON a.caja_id = c.id
        WHERE 1=1
    """
    params: list[Any] = []
    param_idx = 1

    if sucursal_id:
        query += f" AND c.sucursal_id = ${param_idx}"
        params.append(uuid.UUID(sucursal_id))
        param_idx += 1

    if cajero_id:
        query += f" AND a.cajero_id = ${param_idx}"
        params.append(uuid.UUID(cajero_id))
        param_idx += 1

    if fecha_desde:
        query += f" AND cc.fecha_autorizacion_admin >= ${param_idx}"
        params.append(fecha_desde)
        param_idx += 1

    if fecha_hasta:
        query += f" AND cc.fecha_autorizacion_admin <= ${param_idx}"
        params.append(fecha_hasta)
        param_idx += 1

    val = await conn.fetchval(query, *params)
    return int(val or 0)


async def obtener_detalle_cierre(conn: asyncpg.Connection, cierre_id: str) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT
            cc.id,
            cc.apertura_caja_id,
            a.creado AS fecha_apertura,
            cc.fecha_autorizacion_admin AS fecha_cierre,
            a.fondo_inicial,
            cc.monto_cierre AS total_declarado,
            cc.monto_sistema AS total_esperado,
            (cc.monto_cierre - cc.monto_sistema) AS diferencia_neta,
            c.codigo AS terminal,
            COALESCE(s.nombre, 'Sucursal Central') AS sucursal_nombre,
            COALESCE(u_cajero.nombre_completo, u_cajero.email, 'Cajero') AS cajero_nombre,
            COALESCE(u_admin.nombre_completo, u_admin.email, 'Administrador') AS admin_nombre,
            cc.observaciones
        FROM public.cierre_caja cc
        INNER JOIN public.apertura_caja a ON cc.apertura_caja_id = a.id
        INNER JOIN public.cajas c ON a.caja_id = c.id
        LEFT JOIN public.sucursales s ON c.sucursal_id = s.id
        LEFT JOIN public.usuarios u_cajero ON cc.cajero_id = u_cajero.id
        LEFT JOIN public.usuarios u_admin ON cc.administrador_id = u_admin.id
        WHERE cc.id = $1
        """,
        uuid.UUID(cierre_id),
    )
    return dict(row) if row else None
