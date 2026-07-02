"""
app/api/routers/productos.py
Router de productos — solo delega al service.
SAD §3.2 / Regla 11.4: el router nunca accede a un repository ni escribe SQL.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends

from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.services import producto_service

router = APIRouter(prefix="/api/productos", tags=["productos"])


@router.get("/")
async def listar_productos(
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("pos:acceder")),
) -> Any:
    """Lista todos los productos activos."""
    productos = await producto_service.listar_activos(conn)
    return [asdict(p) for p in productos]
