from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

import app.services.paquete_tipos_evento as svc
from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.paquete_tipos_evento import PaqueteTiposEventoCreate, PaqueteTiposEventoOut

router = APIRouter(prefix="/api/paquete-tipos-evento", tags=["Paquete Tipos de Evento"])


@router.get("/{paquete_id}", response_model=list[PaqueteTiposEventoOut])
async def listar_por_paquete(
    paquete_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("paquetes:ver")),
) -> list[PaqueteTiposEventoOut]:
    return await svc.listar_por_paquete(conn, paquete_id)


@router.post("", response_model=PaqueteTiposEventoOut, status_code=status.HTTP_201_CREATED)
async def agregar_tipo_evento(
    body: PaqueteTiposEventoCreate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("paquetes:editar")),
) -> PaqueteTiposEventoOut:
    return await svc.agregar(conn, body)


@router.delete("/{paquete_id}/{tipo_evento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_tipo_evento(
    paquete_id: UUID,
    tipo_evento_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("paquetes:editar")),
) -> None:
    await svc.eliminar(conn, paquete_id, tipo_evento_id)
