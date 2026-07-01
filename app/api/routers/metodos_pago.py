from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

import app.services.metodos_pago as svc
from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.metodos_pago import MetodosPagoCreate, MetodosPagoOut, MetodosPagoUpdate

router = APIRouter(prefix="/api/metodos-pago", tags=["Métodos de Pago"])


@router.get("", response_model=list[MetodosPagoOut])
async def listar_metodos_pago(
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> list[MetodosPagoOut]:
    return await svc.listar(conn)


@router.get("/{metodo_pago_id}", response_model=MetodosPagoOut)
async def obtener_metodo_pago(
    metodo_pago_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> MetodosPagoOut:
    return await svc.obtener(conn, metodo_pago_id)


@router.post("", response_model=MetodosPagoOut, status_code=status.HTTP_201_CREATED)
async def crear_metodo_pago(
    body: MetodosPagoCreate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> MetodosPagoOut:
    return await svc.crear(conn, body)


@router.patch("/{metodo_pago_id}", response_model=MetodosPagoOut)
async def actualizar_metodo_pago(
    metodo_pago_id: UUID,
    body: MetodosPagoUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> MetodosPagoOut:
    return await svc.actualizar(conn, metodo_pago_id, body)


@router.delete("/{metodo_pago_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_metodo_pago(
    metodo_pago_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> None:
    await svc.eliminar(conn, metodo_pago_id)
