from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import TypedDict
from uuid import UUID

import asyncpg


class SucursalRecord(TypedDict):
    id: UUID
    nombre: str
    direccion: str | None
    ciudad: str | None
    estado: str | None
    codigo_postal: str | None
    zona_horaria: str
    hora_apertura: time
    hora_cierre: time
    telefono: str | None
    correo: str | None
    administrador_id: UUID | None
    administrador_name: str | None
    clave: str | None
    activo: bool
    creado: datetime | None
    creado_por: UUID | None
    creador_name: str | None
    modificado: datetime | None
    modificado_por: UUID | None
    modificador_name: str | None


def _row_to_record(row: asyncpg.Record) -> SucursalRecord:
    return SucursalRecord(
        id=row["id"],
        nombre=row["nombre"],
        direccion=row["direccion"],
        ciudad=row["ciudad"],
        estado=row["estado"],
        codigo_postal=row["codigo_postal"],
        zona_horaria=row["zona_horaria"],
        hora_apertura=row["hora_apertura"],
        hora_cierre=row["hora_cierre"],
        telefono=row["telefono"],
        correo=row["correo"],
        administrador_id=row["administrador_id"],
        administrador_name=row["administrador_name"],
        clave=row["clave"],
        activo=row["activo"],
        creado=row["creado"],
        creado_por=row["creado_por"],
        creador_name=row["creador_name"],
        modificado=row.get("modificado"),
        modificado_por=row.get("modificado_por"),
        modificador_name=row.get("modificador_name"),
    )


# Usamos 'uc' para usuario_creador y 'um' para usuario_modificador.
# El administrador de la sucursal ya no es una columna plana: se deriva del
# vínculo real en usuarios_sucursal (permite que el mismo admin esté
# asignado a varias sucursales; ver 010_sucursal_admin_via_puente.sql).
# usuarios_sucursal es genérica (también la usan Cajero/Cocina), así que el
# join se restringe a filas con rol Administrador; y como puede haber más
# de una fila histórica para la misma sucursal (p. ej. datos previos a esta
# migración), se toma como máximo una por sucursal (la más reciente).
_SELECT = """
    SELECT s.id, s.nombre, s.direccion, s.ciudad, s.estado, s.codigo_postal,
           s.zona_horaria, s.hora_apertura, s.hora_cierre, s.telefono, s.correo,
           adm.id AS administrador_id, adm.nombre_completo AS administrador_name,
           s.clave, s.activo,
           s.creado, s.creado_por, uc.nombre_completo AS creador_name,
           s.modificado, s.modificado_por, um.nombre_completo AS modificador_name
    FROM public.sucursales s
    LEFT JOIN public.usuarios uc ON s.creado_por = uc.id
    LEFT JOIN public.usuarios um ON s.modificado_por = um.id
    LEFT JOIN (
        SELECT DISTINCT ON (us.sucursal_id) us.sucursal_id, us.usuario_id
        FROM public.usuarios_sucursal us
        JOIN public.usuarios u ON u.id = us.usuario_id
        JOIN public.roles r ON r.id = u.rol
        WHERE us.activo = TRUE AND r.nombre = 'Administrador'
        ORDER BY us.sucursal_id, us.modificado DESC
    ) admin_link ON admin_link.sucursal_id = s.id
    LEFT JOIN public.usuarios adm ON adm.id = admin_link.usuario_id
"""


async def get_all_sucursales(conn: asyncpg.Connection) -> list[SucursalRecord]:
    rows = await conn.fetch(_SELECT + " ORDER BY s.nombre")
    return [_row_to_record(r) for r in rows]


async def get_sucursal_by_id(conn: asyncpg.Connection, sucursal_id: UUID) -> SucursalRecord | None:
    row = await conn.fetchrow(_SELECT + " WHERE s.id = $1", sucursal_id)
    return _row_to_record(row) if row else None


async def get_sucursal_nombre(conn: asyncpg.Connection, sucursal_id: UUID) -> str | None:
    """Nombre de una sucursal, para adjuntar en las respuestas de auth (login/me)."""
    row = await conn.fetchrow(
        "SELECT nombre FROM public.sucursales WHERE id = $1",
        sucursal_id,
    )
    return row["nombre"] if row else None


class HorarioOperacion(TypedDict):
    hora_apertura: time
    hora_cierre: time


async def get_horario_operacion(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> HorarioOperacion | None:
    """Horario de operación de la sucursal, para el cálculo de bloques de
    disponibilidad (app/services/disponibilidad.py)."""
    row = await conn.fetchrow(
        "SELECT hora_apertura, hora_cierre FROM public.sucursales WHERE id = $1",
        sucursal_id,
    )
    if row is None:
        return None
    return HorarioOperacion(hora_apertura=row["hora_apertura"], hora_cierre=row["hora_cierre"])


async def nombre_exists(conn: asyncpg.Connection, nombre: str) -> bool:
    row = await conn.fetchrow("SELECT id FROM public.sucursales WHERE nombre = $1", nombre)
    return row is not None


class SucursalOption(TypedDict):
    id: UUID
    nombre: str


async def get_sucursales_by_ids(
    conn: asyncpg.Connection, sucursal_ids: list[UUID]
) -> list[SucursalOption]:
    """Nombres de un conjunto de sucursales, para el selector de sucursal activa en login."""
    rows = await conn.fetch(
        """
        SELECT id, nombre FROM public.sucursales
        WHERE id = ANY($1::uuid[]) AND activo = TRUE
        ORDER BY nombre
        """,
        sucursal_ids,
    )
    return [SucursalOption(id=r["id"], nombre=r["nombre"]) for r in rows]


async def create_sucursal(
    conn: asyncpg.Connection,
    nombre: str,
    direccion: str | None,
    telefono: str | None,
    correo: str | None,
    clave: str | None,
    creado_por: UUID,
    ciudad: str | None = None,
    estado: str | None = None,
    codigo_postal: str | None = None,
    zona_horaria: str = "America/Mexico_City",
    hora_apertura: time = time(9, 0),
    hora_cierre: time = time(23, 0),
) -> UUID:
    row = await conn.fetchrow(
        """
        INSERT INTO public.sucursales
            (nombre, direccion, ciudad, estado, codigo_postal, zona_horaria,
             hora_apertura, hora_cierre, telefono, correo, clave, creado_por)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING id
        """,
        nombre,
        direccion,
        ciudad,
        estado,
        codigo_postal,
        zona_horaria,
        hora_apertura,
        hora_cierre,
        telefono,
        correo,
        clave,
        creado_por,
    )
    return UUID(str(row["id"]))


async def update_sucursal(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    clave: str | None,
    nombre: str,
    direccion: str | None,
    telefono: str | None,
    correo: str | None,
    modificado_por: UUID,
    ciudad: str | None = None,
    estado: str | None = None,
    codigo_postal: str | None = None,
    zona_horaria: str = "America/Mexico_City",
    hora_apertura: time = time(9, 0),
    hora_cierre: time = time(23, 0),
) -> bool:
    result = await conn.execute(
        """
        UPDATE public.sucursales
        SET nombre = $1, direccion = $2, telefono = $3, correo = $4,
            clave = $5,
            ciudad = $6, estado = $7, codigo_postal = $8, zona_horaria = $9,
            hora_apertura = $10, hora_cierre = $11,
            modificado = NOW(), modificado_por = $12::uuid
        WHERE id = $13::uuid
        """,
        nombre,  # $1
        direccion,  # $2
        telefono,  # $3
        correo,  # $4
        clave,  # $5
        ciudad,  # $6
        estado,  # $7
        codigo_postal,  # $8
        zona_horaria,  # $9
        hora_apertura,  # $10
        hora_cierre,  # $11
        modificado_por,  # $12
        sucursal_id,
    )
    return str(result) == "UPDATE 1"


async def deactivate_sucursal(
    conn: asyncpg.Connection, sucursal_id: UUID, modificado_por: UUID
) -> bool:
    result = await conn.execute(
        """
        UPDATE public.sucursales
        SET activo = FALSE, modificado = NOW(), modificado_por = $1
        WHERE id = $2 AND activo = TRUE
        """,
        modificado_por,
        sucursal_id,
    )
    return str(result) == "UPDATE 1"


class IndicadoresSucursal(TypedDict):
    ventas: Decimal
    ninos_atendidos: int
    eventos: int
    cajas_abiertas: int


async def get_indicadores_sucursal(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    desde: date,
    hasta: date,
) -> IndicadoresSucursal:
    """Indicadores de solo lectura sobre tablas ya existentes.

    - ventas: comandas cobradas (estado_actual = 'T', entregado) en el rango.
    - ninos_atendidos: niños distintos con un detalle de registro cuya
      entrada cae en el rango.
    - eventos: reservaciones activas, no canceladas, con fecha_evento en el
      rango.
    - cajas_abiertas: foto actual (no depende de desde/hasta) de cuántas
      cajas de la sucursal tienen un turno abierto ahora mismo.
    """
    ventas = await conn.fetchval(
        """
        SELECT COALESCE(SUM(total_final), 0)
        FROM public.comandas
        WHERE sucursal_id = $1
          AND estado_actual = 'T'
          AND fecha_hora::date BETWEEN $2 AND $3
        """,
        sucursal_id,
        desde,
        hasta,
    )
    ninos_atendidos = await conn.fetchval(
        """
        SELECT COUNT(DISTINCT dr.ninos_id)
        FROM public.detalles_registro dr
        WHERE dr.sucursal_id = $1
          AND dr.activo = TRUE
          AND dr.entrada::date BETWEEN $2 AND $3
        """,
        sucursal_id,
        desde,
        hasta,
    )
    eventos = await conn.fetchval(
        """
        SELECT COUNT(*)
        FROM public.reservaciones
        WHERE sucursal_id = $1
          AND activo = TRUE
          AND estado != 'cancelada'
          AND fecha_evento BETWEEN $2 AND $3
        """,
        sucursal_id,
        desde,
        hasta,
    )
    cajas_abiertas = await conn.fetchval(
        """
        SELECT COUNT(*)
        FROM public.apertura_caja a
        JOIN public.cajas c ON c.id = a.caja_id
        WHERE c.sucursal_id = $1
          AND a.estado IN ('ABIERTA', 'EN_CORTE')
        """,
        sucursal_id,
    )
    return IndicadoresSucursal(
        ventas=ventas,
        ninos_atendidos=ninos_atendidos,
        eventos=eventos,
        cajas_abiertas=cajas_abiertas,
    )


async def reactivate_sucursal(
    conn: asyncpg.Connection, sucursal_id: UUID, modificado_por: UUID
) -> bool:
    result = await conn.execute(
        """
        UPDATE public.sucursales
        SET activo = TRUE, modificado = NOW(), modificado_por = $1
        WHERE id = $2 AND activo = FALSE
        """,
        modificado_por,
        sucursal_id,
    )
    return str(result) == "UPDATE 1"
