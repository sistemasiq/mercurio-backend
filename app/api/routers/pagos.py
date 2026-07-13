from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

import app.services.pago_service as svc
from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.pagos import PaymentOut, PaymentRequest

router = APIRouter(prefix="/api/pagos", tags=["Pagos"])


@router.post(
    "",
    response_model=list[PaymentOut],
    status_code=status.HTTP_201_CREATED,
    summary="Registrar pagos de una comanda",
    description=(
        "Recibe uno o más pagos asociados a una comanda, valida que "
        "el total coincida con el esperado y los persiste en pagos_ordenes."
    ),
)
async def registrar_pagos(
    body: PaymentRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("restaurante:registrar_pago")),
) -> list[PaymentOut]:
    usuario_id = UUID(current_user.sub)
    return await svc.procesar_pagos(conn, body, usuario_id)
