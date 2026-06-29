from __future__ import annotations

import asyncpg

from app.repositories.permission_repository import (
    PermisoRecord,
    RolRecord,
    get_all_permisos,
    get_all_rol_permisos_cache,
    get_all_roles,
    get_permisos_por_rol,
    get_rol_by_id,
    set_rol_permisos,
)
from app.schemas.permission import PermisoResponse, RolConPermisosResponse


class RolNotFoundError(Exception):
    pass


class PermisoInvalidoError(Exception):
    pass


# Caché en memoria: {nombre_rol: frozenset(codigos_permiso)}
# Se carga al arrancar la app y se invalida al editar permisos.
_cache: dict[str, frozenset[str]] = {}


async def load_cache(conn: asyncpg.Connection) -> None:
    """Carga el caché de permisos desde BD. Llamar en el lifespan de la app."""
    global _cache
    raw = await get_all_rol_permisos_cache(conn)
    _cache = {rol: frozenset(codigos) for rol, codigos in raw.items()}


def has_permission(role_name: str, permission_code: str) -> bool:
    """Devuelve True si el rol tiene el permiso indicado."""
    return permission_code in _cache.get(role_name, frozenset())


def _permiso_to_response(r: PermisoRecord) -> PermisoResponse:
    return PermisoResponse(
        id=r["id"],
        codigo=r["codigo"],
        nombre=r["nombre"],
        modulo=r["modulo"],
        descripcion=r["descripcion"],
    )


def _rol_to_response(rol: RolRecord, permisos: list[PermisoRecord]) -> RolConPermisosResponse:
    return RolConPermisosResponse(
        id=rol["id"],
        nombre=rol["nombre"],
        descripcion=rol["descripcion"],
        permisos=[_permiso_to_response(p) for p in permisos],
    )


async def list_roles(conn: asyncpg.Connection) -> list[RolConPermisosResponse]:
    roles = await get_all_roles(conn)
    result = []
    for rol in roles:
        permisos = await get_permisos_por_rol(conn, rol["id"])
        result.append(_rol_to_response(rol, permisos))
    return result


async def get_rol(conn: asyncpg.Connection, rol_id: int) -> RolConPermisosResponse:
    rol = await get_rol_by_id(conn, rol_id)
    if rol is None:
        raise RolNotFoundError
    permisos = await get_permisos_por_rol(conn, rol_id)
    return _rol_to_response(rol, permisos)


async def list_permisos(conn: asyncpg.Connection) -> list[PermisoResponse]:
    permisos = await get_all_permisos(conn)
    return [_permiso_to_response(p) for p in permisos]


async def update_rol_permisos(
    conn: asyncpg.Connection, rol_id: int, permiso_ids: list[int]
) -> RolConPermisosResponse:
    rol = await get_rol_by_id(conn, rol_id)
    if rol is None:
        raise RolNotFoundError

    all_permisos = await get_all_permisos(conn)
    valid_ids = {p["id"] for p in all_permisos}
    invalid = [pid for pid in permiso_ids if pid not in valid_ids]
    if invalid:
        raise PermisoInvalidoError

    async with conn.transaction():
        await set_rol_permisos(conn, rol_id, permiso_ids)

    # Recargar caché completo
    await load_cache(conn)

    permisos = await get_permisos_por_rol(conn, rol_id)
    return _rol_to_response(rol, permisos)
