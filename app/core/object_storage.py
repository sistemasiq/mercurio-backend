import asyncio
import logging
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.core.config import settings
from app.exceptions import DatosInvalidos, NoEncontrado

logger = logging.getLogger(__name__)

PREFIJOS = {
    "identificaciones": "uploads/identificaciones",
    "llegadas": "uploads/llegadas",
    "productos": "uploads/productos",
}

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB

_client = boto3.client(
    "s3",
    endpoint_url=f"http{'s' if settings.minio_secure else ''}://{settings.minio_endpoint}",
    aws_access_key_id=settings.minio_access_key,
    aws_secret_access_key=settings.minio_secret_key,
    config=Config(signature_version="s3v4"),
)

BUCKET = settings.minio_bucket


def _crear_bucket() -> None:
    try:
        _client.head_bucket(Bucket=BUCKET)
    except ClientError:
        _client.create_bucket(Bucket=BUCKET)


async def ensure_bucket() -> None:
    """Crea el bucket si no existe. Se llama una vez al arrancar la app."""
    await asyncio.to_thread(_crear_bucket)


async def validar_y_leer(imagen: UploadFile) -> bytes:
    """Valida tipo y tamaño de una imagen subida y retorna sus bytes."""
    if imagen.content_type not in ALLOWED_CONTENT_TYPES:
        raise DatosInvalidos("El archivo debe ser una imagen JPEG o PNG.")

    data = await imagen.read()
    if len(data) > MAX_SIZE:
        raise DatosInvalidos("La imagen no debe superar los 5 MB.")

    return data


async def upload_bytes(key: str, data: bytes, content_type: str) -> None:
    await asyncio.to_thread(
        _client.put_object, Bucket=BUCKET, Key=key, Body=data, ContentType=content_type
    )


def _get_object(key: str) -> dict[str, Any]:
    try:
        return _client.get_object(Bucket=BUCKET, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code in ("NoSuchKey", "404"):
            raise NoEncontrado("Archivo") from e
        raise


async def get_object(key: str) -> tuple[Any, str]:
    """Retorna (stream, content_type) del objeto sin cargarlo completo a memoria."""
    obj = await asyncio.to_thread(_get_object, key)
    return obj["Body"], obj.get("ContentType", "application/octet-stream")
