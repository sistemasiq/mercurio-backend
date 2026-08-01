from typing import Any
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from starlette import status

from app.api.deps import apertura_operando_id, require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.pagos import PagoIn
from app.schemas.registros import (
    CheckoutResponse,
    DetalleActivoResponse,
    OnboardingRequest,
    OnboardingResponse,
    ProductoResponse,
)
from app.services.chekouts import create_chekout
from app.services.estancias import (
    create_estancia,
    get_activos_estancia_by_sucursal_id,
    get_productos_estancia_by_id_sucursal,
)
from app.services.pagos_estancia import pago_create_service

# Tipo A (acción sobre un id): "/{id}/verbo" — /{registro_id}/pagos, /{detalle_id}/checkout.
# Tipo B (sub-colección filtrada, no acción): "/verbo/{id}" — /activos/{sucursal_id},
# /productos/{sucursal_id}. Ver RUTAS.md §5.5.
router = APIRouter(prefix="/api/estancias", tags=["Estancias"])


@router.get(
    "/activos/{sucursal_id}",
    response_model=list[DetalleActivoResponse],
    summary="Listar niños en estancia",
    description="Consulta todos los niños que se encuentran activos actualmente en la sucursal.",
)
async def get_activos(
    sucursal_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("estancias:ver_activos")),
) -> list[dict[str, Any]]:
    return await get_activos_estancia_by_sucursal_id(conn, sucursal_id)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=OnboardingResponse,
    summary="Registrar entrada de niños",
    description=(
        "Crea un registro de entrada completo vinculando al tutor, "
        "los niños y procesando el pago inicial."
    ),
)
async def onboarding(
    fotoIne: UploadFile = File(...),  # noqa: N803 - nombre del campo multipart del front
    fotoLlegada: UploadFile = File(...),  # noqa: N803 - nombre del campo multipart del front
    payload: str = Form(..., description="JSON string con los datos de OnboardingRequest"),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("estancias:checkin")),
    apertura_id: str = Depends(apertura_operando_id),
) -> dict[str, Any]:
    try:
        data = OnboardingRequest.model_validate_json(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from e

    usuario_id = UUID(current_user.sub)

    return await create_estancia(conn, data, fotoIne, fotoLlegada, usuario_id, apertura_id)


@router.post(
    "/{registro_id}/pagos",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar pago adicional",
    description=(
        "Registra uno o más pagos extraordinarios vinculados "
        "a un registro de estancia existente."
    ),
)
async def pago_estancia_extra(
    registro_id: UUID,
    pagos: list[PagoIn],
    sucursal_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("estancias:gestionar_pagos")),
    apertura_id: str = Depends(apertura_operando_id),
) -> None:
    usuario_id = UUID(current_user.sub)
    return await pago_create_service(conn, pagos, sucursal_id, registro_id, usuario_id, apertura_id)


# Endpoint para calcular checkout
@router.post(
    "/{detalle_id}/checkout",
    status_code=status.HTTP_201_CREATED,
    response_model=CheckoutResponse,
    summary="Procesar salida del niño",
    description=(
        "Registra la salida, calcula cargos extra por tiempo y marca "
        "el registro como finalizado si corresponde."
    ),
)
async def checkout(
    detalle_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("estancias:checkout")),
    __: str = Depends(apertura_operando_id),
) -> dict[str, Any]:
    usuario_id = UUID(current_user.sub)

    return await create_chekout(conn, detalle_id, usuario_id)


@router.get(
    "/productos/{sucursal_id}",
    response_model=list[ProductoResponse],
    summary="Listar productos",
    description="Obtiene el catálogo de productos tipo 'estancia' activos para la sucursal.",
)
async def get_productos(
    sucursal_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("estancias:checkin")),
) -> list[dict[str, Any]]:
    return await get_productos_estancia_by_id_sucursal(conn, sucursal_id)
