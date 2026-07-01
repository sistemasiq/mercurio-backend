"""
app/services/producto_service.py
Lógica de negocio para productos.
SAD §3.2: el service orquesta repositorios, nunca escribe SQL directamente.
"""

from __future__ import annotations

import asyncpg

from app.models.producto import Producto
from app.repositories import producto_repository


async def listar_activos(conn: asyncpg.Connection) -> list[Producto]:
    """Retorna todos los productos activos."""
    return await producto_repository.get_productos_activos(conn)
