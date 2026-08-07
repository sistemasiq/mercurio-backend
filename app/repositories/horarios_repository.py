"""
app/repositories/horarios_repository.py
Operaciones de BD para el CRUD administrativo de horarios (tabla turnos).
"""

from __future__ import annotations

import uuid
from datetime import datetime, time

import asyncpg

from app.core.utils import get_mexico_now


def _parse_time(t: str | None) -> time | None:
    if t is None:
        return None
    return time.fromisoformat(t)


def _fmt_time(t: object) -> str:
    """Convierte datetime.time a 'HH:MM'."""
    if hasattr(t, "strftime"):
        return t.strftime("%H:%M")  # type: ignore[union-attr]
    return str(t)[:5]


def _row_to_dict(row: asyncpg.Record) -> dict:
    d = dict(row)
    d["id"] = str(d["id"])
    d["hora_inicio"] = _fmt_time(d["hora_inicio"])
    d["hora_fin"] = _fmt_time(d["hora_fin"])
    return d


async def listar_horarios(conn: asyncpg.Connection) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT id, nombre, hora_inicio, hora_fin, activo
        FROM public.turnos
        ORDER BY hora_inicio ASC, nombre ASC
        """
    )
    return [_row_to_dict(r) for r in rows]


async def get_horario_por_id(conn: asyncpg.Connection, horario_id: str) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT id, nombre, hora_inicio, hora_fin, activo
        FROM public.turnos
        WHERE id = $1
        """,
        uuid.UUID(horario_id),
    )
    return _row_to_dict(row) if row else None


async def crear_horario(
    conn: asyncpg.Connection,
    nombre: str,
    hora_inicio: str,
    hora_fin: str,
    creado_por: str | None = None,
) -> dict:
    now = get_mexico_now()
    row = await conn.fetchrow(
        """
        INSERT INTO public.turnos (id, nombre, hora_inicio, hora_fin, activo, creado, creado_por)
        VALUES (gen_random_uuid(), $1, $2::time, $3::time, TRUE, $4, $5)
        RETURNING id, nombre, hora_inicio, hora_fin, activo
        """,
        nombre,
        _parse_time(hora_inicio),
        _parse_time(hora_fin),
        now,
        uuid.UUID(creado_por) if creado_por else None,
    )
    return _row_to_dict(row)


async def actualizar_horario(
    conn: asyncpg.Connection,
    horario_id: str,
    nombre: str | None = None,
    hora_inicio: str | None = None,
    hora_fin: str | None = None,
    activo: bool | None = None,
    modificado_por: str | None = None,
) -> dict | None:
    current = await get_horario_por_id(conn, horario_id)
    if current is None:
        return None

    now = get_mexico_now()
    row = await conn.fetchrow(
        """
        UPDATE public.turnos
        SET
            nombre      = COALESCE($2, nombre),
            hora_inicio = COALESCE($3::time, hora_inicio),
            hora_fin    = COALESCE($4::time, hora_fin),
            activo      = COALESCE($5, activo),
            modificado  = $6,
            modificado_por = $7
        WHERE id = $1
        RETURNING id, nombre, hora_inicio, hora_fin, activo
        """,
        uuid.UUID(horario_id),
        nombre,
        _parse_time(hora_inicio),
        _parse_time(hora_fin),
        activo,
        now,
        uuid.UUID(modificado_por) if modificado_por else None,
    )
    return _row_to_dict(row) if row else None


async def eliminar_horario(
    conn: asyncpg.Connection,
    horario_id: str,
    modificado_por: str | None = None,
) -> bool:
    """Borrado lógico: activo = FALSE. Devuelve True si la fila existía."""
    now = get_mexico_now()
    result = await conn.execute(
        """
        UPDATE public.turnos
        SET activo = FALSE, modificado = $2, modificado_por = $3
        WHERE id = $1
        """,
        uuid.UUID(horario_id),
        now,
        uuid.UUID(modificado_por) if modificado_por else None,
    )
    return result != "UPDATE 0"
