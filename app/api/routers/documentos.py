from typing import Any
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user, get_db
from app.core.object_storage import PREFIJOS, get_object
from app.schemas.auth import TokenData
from app.services.documentos_service import obtener_fotos_llegada_por_registro

router = APIRouter(prefix="/api/uploads", tags=["Archivos Protegidos"])


@router.get("/productos/{nombre_archivo}")
async def descargar_imagen_producto(nombre_archivo: str) -> StreamingResponse:
    """Sirve las fotos de productos sin autenticación: se muestran en <img>/q-img
    en la caja y el catálogo, que no pueden enviar el header Authorization."""
    key = f"{PREFIJOS['productos']}/{nombre_archivo}"
    body, content_type = await get_object(key)

    return StreamingResponse(body, media_type=content_type)

@router.get("/registros/{registro_id}/llegadas")
async def descargar_imagenes_llegada(
    registro_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> StreamingResponse:
    """Obtiene un ZIP con las fotos de llegada asociadas a un registro de estancia."""
    return await obtener_fotos_llegada_por_registro(conn, str(registro_id))

@router.get("/{carpeta}/{nombre_archivo}")
async def descargar_archivo_protegido(
    carpeta: str,
    nombre_archivo: str,
    _: TokenData = Depends(get_current_user),
) -> StreamingResponse:
    if carpeta not in PREFIJOS:
        raise HTTPException(status_code=400, detail="Directorio no permitido.")

    key = f"{PREFIJOS[carpeta]}/{nombre_archivo}"
    body, content_type = await get_object(key)

    return StreamingResponse(body, media_type=content_type)
