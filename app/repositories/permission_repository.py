from __future__ import annotations

from typing import TypedDict

import asyncpg


class RolRecord(TypedDict):
    id: int
    nombre: str
    descripcion: str | None
    activo: bool


class PermisoRecord(TypedDict):
    id: int
    codigo: str
    nombre: str
    modulo: str
    descripcion: str | None


def _row_to_rol(row: asyncpg.Record) -> RolRecord:
    return RolRecord(
        id=row["id"],
        nombre=row["nombre"],
        descripcion=row["descripcion"],
        activo=row["activo"],
    )


def _row_to_permiso(row: asyncpg.Record) -> PermisoRecord:
    return PermisoRecord(
        id=row["id"],
        codigo=row["codigo"],
        nombre=row["nombre"],
        modulo=row["modulo"],
        descripcion=row["descripcion"],
    )


async def get_all_roles(conn: asyncpg.Connection) -> list[RolRecord]:
    rows = await conn.fetch("SELECT id, nombre, descripcion, activo FROM public.roles ORDER BY id")
    return [_row_to_rol(r) for r in rows]


async def get_rol_by_id(conn: asyncpg.Connection, rol_id: int) -> RolRecord | None:
    row = await conn.fetchrow(
        "SELECT id, nombre, descripcion, activo FROM public.roles WHERE id = $1",
        rol_id,
    )
    return _row_to_rol(row) if row else None


async def get_rol_by_nombre(conn: asyncpg.Connection, nombre: str) -> RolRecord | None:
    row = await conn.fetchrow(
        "SELECT id, nombre, descripcion, activo FROM public.roles WHERE nombre = $1",
        nombre,
    )
    return _row_to_rol(row) if row else None


async def get_all_permisos(conn: asyncpg.Connection) -> list[PermisoRecord]:
    rows = await conn.fetch(
        "SELECT id, codigo, nombre, modulo, descripcion"
        " FROM public.permisos ORDER BY modulo, codigo"
    )
    return [_row_to_permiso(r) for r in rows]


async def get_permisos_por_rol(conn: asyncpg.Connection, rol_id: int) -> list[PermisoRecord]:
    rows = await conn.fetch(
        """
        SELECT p.id, p.codigo, p.nombre, p.modulo, p.descripcion
        FROM public.rol_permisos rp
        JOIN public.permisos p ON p.id = rp.permiso_id
        WHERE rp.rol_id = $1
        ORDER BY p.modulo, p.codigo
        """,
        rol_id,
    )
    return [_row_to_permiso(r) for r in rows]


async def get_all_rol_permisos_cache(conn: asyncpg.Connection) -> dict[str, set[str]]:
    """Devuelve {nombre_rol: {codigo_permiso, ...}} para construir el caché."""
    rows = await conn.fetch(
        """
        SELECT r.nombre AS rol_nombre, p.codigo
        FROM public.rol_permisos rp
        JOIN public.roles r   ON r.id = rp.rol_id
        JOIN public.permisos p ON p.id = rp.permiso_id
        """
    )
    result: dict[str, set[str]] = {}
    for row in rows:
        rol = row["rol_nombre"]
        if rol not in result:
            result[rol] = set()
        result[rol].add(row["codigo"])
    return result


async def create_rol(conn: asyncpg.Connection, nombre: str, descripcion: str | None) -> int:
    row = await conn.fetchrow(
        "INSERT INTO public.roles (nombre, descripcion) VALUES ($1, $2) RETURNING id",
        nombre,
        descripcion,
    )
    rol_id: int = row["id"]
    return rol_id


async def update_rol_metadata(
    conn: asyncpg.Connection,
    rol_id: int,
    nombre: str | None,
    descripcion: str | None,
    activo: bool | None,
    update_descripcion: bool,
) -> None:
    """Actualiza solo los campos indicados. `descripcion` puede ser un
    None deliberado (borrarla), por eso `update_descripcion` distingue
    "no tocar" de "poner en null"."""
    if nombre is not None:
        await conn.execute("UPDATE public.roles SET nombre = $1 WHERE id = $2", nombre, rol_id)
    if update_descripcion:
        await conn.execute(
            "UPDATE public.roles SET descripcion = $1 WHERE id = $2", descripcion, rol_id
        )
    if activo is not None:
        await conn.execute("UPDATE public.roles SET activo = $1 WHERE id = $2", activo, rol_id)


async def set_rol_permisos(conn: asyncpg.Connection, rol_id: int, permiso_ids: list[int]) -> None:
    """Reemplaza todos los permisos del rol. Ejecutar dentro de una transacción."""
    await conn.execute("DELETE FROM public.rol_permisos WHERE rol_id = $1", rol_id)
    if permiso_ids:
        await conn.executemany(
            "INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES ($1, $2)",
            [(rol_id, pid) for pid in permiso_ids],
        )
