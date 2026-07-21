from app.schemas.extras import ExtrasCrear
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_session
from app.db.security import get_current_user

from app.schemas.extras import ExtrasOut
from app.services import extras as sExtras

router = APIRouter(prefix="/extras", tags=["Extras"])

@router.get("/", response_model=list[ExtrasOut], summary="Listar todos los extras")
async def get_all_extras(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    
    Obtiene todos los extras disponibles.
    
    Args:
        db: Sesión asíncrona con la base de datos
        current_user: Usuario actual autenticado
        
    Returns:
        Lista de extras
    """
    return await sExtras.get_all_extras(db)
@router.get("/{id}", response_model=ExtrasOut, summary="Obtener un extra por ID")
async def get_extra_by_id(
    id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    
    Obtiene un extra por ID.
    
    Args:
        id: ID del extra a obtener
        db: Sesión asíncrona con la base de datos
        current_user: Usuario actual autenticado
        
    Returns:
        Extra solicitado
    """
    return await sExtras.get_extra_by_id(db, id)    

@router.post("/", response_model=ExtrasOut, summary="Crear un nuevo extra")
async def create_extra(
    extra: ExtrasCrear,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    
    Crea un nuevo extra.
    
    Args:
        extra: Datos del extra a crear
        db: Sesión asíncrona con la base de datos
        current_user: Usuario actual autenticado
        
    Returns:
        Extra creado
    """
    return await sExtras.create_extra(db, extra, current_user)

@router.put("/{id}", response_model=ExtrasOut, summary="Actualizar un extra")
async def update_extra(
    id: int,
    extra: ExtrasCrear,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    
    Actualiza un extra existente.
    
    Args:
        id: ID del extra a actualizar
        extra: Datos del extra a actualizar
        db: Sesión asíncrona con la base de datos
        current_user: Usuario actual autenticado
        
    Returns:
        Extra actualizado
    """
    return await sExtras.update_extra(db, id, extra, current_user)

@router.delete("/{id}", response_model=ExtrasOut, summary="Eliminar un extra")
async def delete_extra(
    id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    
    Elimina un extra existente.
    
    Args:
        id: ID del extra a eliminar
        db: Sesión asíncrona con la base de datos
        current_user: Usuario actual autenticado
        
    Returns:
        Extra eliminado
    """
    return await sExtras.delete_extra(db, id, current_user)
    
