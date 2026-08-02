"""
app/services/unidad_medida_service.py
Lógica de negocio para el catálogo de unidades de medida.
SAD §3.2: el service orquesta repositorios, nunca escribe SQL directamente.
"""

from __future__ import annotations

import asyncpg

from app.repositories import unidad_medida_repository
from app.schemas.unidad_medida import UnidadMedidaOut


async def listar(conn: asyncpg.Connection) -> list[UnidadMedidaOut]:
    rows = await unidad_medida_repository.listar(conn)
    return [UnidadMedidaOut.model_validate(r) for r in rows]
