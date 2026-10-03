"""
app/api/routers/unidades_medida.py
Router de unidades de medida — solo lectura, el catálogo se siembra por
migración (fase 1 de inventario). El router nunca accede a un repository ni
escribe SQL.
"""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends

from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.unidad_medida import UnidadMedidaOut
from app.services import unidad_medida_service

router = APIRouter(prefix="/api/unidades-medida", tags=["Unidades de Medida"])


@router.get("", response_model=list[UnidadMedidaOut])
async def listar_unidades_medida(
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("inventario:ver")),
) -> list[UnidadMedidaOut]:
    """Lista las unidades de medida activas, para poblar selects al crear insumos."""
    return await unidad_medida_service.listar(conn)
