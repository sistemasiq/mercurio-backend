import io
from typing import Any

import asyncpg
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from zipfile import ZipFile

from app.core.object_storage import get_object
from app.exceptions import NoEncontrado
from app.repositories.fotos import get_fotos_llegada_by_registro_id


async def obtener_fotos_llegada_por_registro(
    conn: asyncpg.Connection,
    registro_id: str,
) -> StreamingResponse:
    """Obtiene un ZIP con las fotos de llegada asociadas a un registro de estancia."""
    fotos = await get_fotos_llegada_by_registro_id(conn, registro_id)

    if not fotos:
        raise HTTPException(status_code=404, detail="No se encontraron fotos de llegada para este registro")

    zip_buffer = io.BytesIO()

    with ZipFile(zip_buffer, 'w') as zip_file:
        for idx, foto in enumerate(fotos):
            storage_url = foto["storage_url"]
            nombre_archivo = storage_url.split('/')[-1]

            try:
                stream, content_type = await get_object(storage_url)
                image_data = stream.read()
                zip_file.writestr(f"foto_{idx+1}_{nombre_archivo}", image_data)
            except NoEncontrado:
                continue

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=fotos_llegada_{registro_id}.zip"
        }
    )
