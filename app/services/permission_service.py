from __future__ import annotations

import asyncpg

from app.core.roles import ROL_SISTEMA, ROLES_SIN_SUCURSAL_FIJA
from app.repositories.permission_repository import (
    PermisoRecord,
    RolRecord,
    create_rol as insert_rol,
    get_all_permisos,
    get_all_rol_permisos_cache,
    get_all_roles,
    get_permisos_por_rol,
    get_rol_by_id,
    get_rol_by_nombre,
    set_rol_permisos,
    update_rol_metadata,
)
from app.schemas.permission import PermisoResponse, RolConPermisosResponse, RolUpdateRequest


class RolNotFoundError(Exception):
    pass


class PermisoInvalidoError(Exception):
    pass


class RolNombreDuplicadoError(Exception):
    pass


class RolProtegidoError(Exception):
    """Los roles estructurales (ROLES_SIN_SUCURSAL_FIJA) no se pueden renombrar
    ni desactivar; AdministradorSistema tampoco puede perder permisos."""


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


def get_permissions(role_name: str) -> list[str]:
    """Devuelve los códigos de permiso del rol, para incluir como claim en el JWT."""
    return sorted(_cache.get(role_name, frozenset()))


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
        activo=rol["activo"],
        requiere_sucursal=rol["nombre"] not in ROLES_SIN_SUCURSAL_FIJA,
        permisos_editables=rol["nombre"] != ROL_SISTEMA,
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
    if rol["nombre"] == ROL_SISTEMA:
        raise RolProtegidoError

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


async def create_rol(
    conn: asyncpg.Connection, nombre: str, descripcion: str | None, permiso_ids: list[int]
) -> RolConPermisosResponse:
    if await get_rol_by_nombre(conn, nombre) is not None:
        raise RolNombreDuplicadoError

    all_permisos = await get_all_permisos(conn)
    valid_ids = {p["id"] for p in all_permisos}
    if any(pid not in valid_ids for pid in permiso_ids):
        raise PermisoInvalidoError

    async with conn.transaction():
        rol_id = await insert_rol(conn, nombre, descripcion)
        if permiso_ids:
            await set_rol_permisos(conn, rol_id, permiso_ids)

    await load_cache(conn)

    rol = await get_rol_by_id(conn, rol_id)
    assert rol is not None
    permisos = await get_permisos_por_rol(conn, rol_id)
    return _rol_to_response(rol, permisos)


async def update_rol(
    conn: asyncpg.Connection, rol_id: int, body: RolUpdateRequest
) -> RolConPermisosResponse:
    rol = await get_rol_by_id(conn, rol_id)
    if rol is None:
        raise RolNotFoundError

    campos_estructurales = rol["nombre"] in ROLES_SIN_SUCURSAL_FIJA
    renombra = body.nombre is not None and body.nombre != rol["nombre"]
    desactiva = body.activo is False
    if campos_estructurales and (renombra or desactiva):
        raise RolProtegidoError

    nombre_en_uso = renombra and await get_rol_by_nombre(conn, body.nombre or "") is not None
    if nombre_en_uso:
        raise RolNombreDuplicadoError

    async with conn.transaction():
        await update_rol_metadata(
            conn,
            rol_id,
            nombre=body.nombre,
            descripcion=body.descripcion,
            activo=body.activo,
            update_descripcion="descripcion" in body.model_fields_set,
        )

    # Recargar caché: un rol desactivado/reactivado no cambia sus permisos,
    # pero un rename sí cambia la clave con la que se cachean (nombre_rol).
    await load_cache(conn)

    rol = await get_rol_by_id(conn, rol_id)
    assert rol is not None
    permisos = await get_permisos_por_rol(conn, rol_id)
    return _rol_to_response(rol, permisos)
