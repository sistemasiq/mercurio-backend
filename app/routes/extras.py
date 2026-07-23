from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.extras import ExtrasCrear, ExtrasOut, ExtrasUpdate
from app.services import extras as sExtras

router = APIRouter(prefix="/extras", tags=["Extras"])

@router.get("/", response_model=list[ExtrasOut], summary="Listar todos los extras")
async def get_all_extras(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """

    Obtiene todos los extras disponibles.

    Args:
        conn: Conexión asíncrona con la base de datos
        current_user: Usuario actual autenticado

    Returns:
        Lista de extras
    """
    return await sExtras.listar(conn)
@router.get("/{id}", response_model=ExtrasOut, summary="Obtener un extra por ID")
async def get_extra_by_id(
    id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """

    Obtiene un extra por ID.

    Args:
        id: ID del extra a obtener
        conn: Conexión asíncrona con la base de datos
        current_user: Usuario actual autenticado

    Returns:
        Extra solicitado
    """
    return await sExtras.obtener(conn, id)

@router.post("/", response_model=ExtrasOut, summary="Crear un nuevo extra")
async def create_extra(
    extra: ExtrasCrear,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """

    Crea un nuevo extra.

    Args:
        extra: Datos del extra a crear
        conn: Conexión asíncrona con la base de datos
        current_user: Usuario actual autenticado

    Returns:
        Extra creado
    """
    return await sExtras.crear(conn, extra)

@router.put("/{id}", response_model=ExtrasOut, summary="Actualizar un extra")
async def update_extra(
    id: UUID,
    extra: ExtrasUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """

    Actualiza un extra existente.

    Args:
        id: ID del extra a actualizar
        extra: Datos del extra a actualizar
        conn: Conexión asíncrona con la base de datos
        current_user: Usuario actual autenticado

    Returns:
        Extra actualizado
    """
    return await sExtras.actualizar(conn, id, extra)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un extra")
async def delete_extra(
    id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """

    Elimina un extra existente.

    Args:
        id: ID del extra a eliminar
        conn: Conexión asíncrona con la base de datos
        current_user: Usuario actual autenticado

    Returns:
        Extra eliminado
    """
    await sExtras.eliminar(conn, id)
