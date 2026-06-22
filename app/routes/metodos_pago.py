from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.dependencies import get_current_user
from app.schemas.metodos_pago import MetodosPagoCreate, MetodosPagoOut, MetodosPagoUpdate
import app.services.metodos_pago as svc

router = APIRouter(prefix="/api/metodos-pago", tags=["Métodos de Pago"])


@router.get("", response_model=list[MetodosPagoOut])
async def listar_metodos_pago(
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.listar(session)


@router.get("/{metodo_pago_id}", response_model=MetodosPagoOut)
async def obtener_metodo_pago(
    metodo_pago_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.obtener(session, metodo_pago_id)


@router.post("", response_model=MetodosPagoOut, status_code=status.HTTP_201_CREATED)
async def crear_metodo_pago(
    body: MetodosPagoCreate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.crear(session, body)


@router.patch("/{metodo_pago_id}", response_model=MetodosPagoOut)
async def actualizar_metodo_pago(
    metodo_pago_id: UUID,
    body: MetodosPagoUpdate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.actualizar(session, metodo_pago_id, body)


@router.delete("/{metodo_pago_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_metodo_pago(
    metodo_pago_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    await svc.eliminar(session, metodo_pago_id)
