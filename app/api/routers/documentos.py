from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.storage import IDENTIFICACIONES_DIR, LLEGADAS_DIR

router = APIRouter(prefix="/api/uploads", tags=["Archivos Protegidos"])

DIRECTORIOS = {"identificaciones": IDENTIFICACIONES_DIR, "llegadas": LLEGADAS_DIR}


@router.get("/{carpeta}/{nombre_archivo}")
async def descargar_archivo_protegido(carpeta: str, nombre_archivo: str) -> FileResponse:
    if carpeta not in DIRECTORIOS:
        raise HTTPException(status_code=400, detail="Directorio no permitido.")

    ruta_archivo = (DIRECTORIOS[carpeta] / nombre_archivo).resolve()

    if not ruta_archivo.is_relative_to(DIRECTORIOS[carpeta].resolve()):
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    if not ruta_archivo.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    return FileResponse(str(ruta_archivo))
