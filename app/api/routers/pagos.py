from dataclasses import asdict
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

import app.services.pago_service as svc
from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.pagos import PaymentOut, PaymentRequest, PagoCompletoRequest

router = APIRouter(prefix="/api/pagos", tags=["Pagos"])


def _get_active_branch(current_user: TokenData) -> UUID:
    if current_user.branch_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La sesión no tiene una sucursal activa.",
        )
    return current_user.branch_id


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


@router.post(
    "/completar",
    status_code=status.HTTP_201_CREATED,
    summary="Crear comanda y registrar pagos en una transacción",
    description=(
        "Recibe los datos de la comanda y los pagos. Crea la comanda, "
        "registra los pagos y notifica a cocina en una única transacción. "
        "Si falla cualquiera de los dos, nada se persiste."
    ),
)
async def completar_pago(
    body: PagoCompletoRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("restaurante:registrar_pago")),
) -> dict:
    usuario_id = UUID(current_user.sub)
    sucursal_id = _get_active_branch(current_user)
    comanda = await svc.completar_pago(conn, body, usuario_id, sucursal_id)
    return asdict(comanda)
