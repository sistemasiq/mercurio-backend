"""
app/services/comanda_service.py
Lógica de negocio para comandas.
SAD §3.2: el service orquesta repositorios, nunca escribe SQL directamente.
"""

from __future__ import annotations

import asyncpg

from app.models.comanda import Comanda
from app.repositories import comanda_repository
from app.schemas.comanda import ComandaCreate


async def crear_comanda(conn: asyncpg.Connection, comanda_in: ComandaCreate) -> Comanda:
    """Crea una comanda con sus detalles."""
    return await comanda_repository.crear_comanda_con_detalles(conn, comanda_in)


async def listar_pendientes(conn: asyncpg.Connection) -> list[Comanda]:
    """Retorna las comandas activas (estados P, E, L)."""
    return await comanda_repository.get_comandas_pendientes(conn)


async def cambiar_estado(
    conn: asyncpg.Connection,
    comanda_id: str,
    nuevo_estado: str,
) -> Comanda | None:
    """
    Actualiza el estado de una comanda.
    Retorna None si la comanda no existe.
    """
    return await comanda_repository.actualizar_estado_comanda(conn, comanda_id, nuevo_estado)


async def obtener_por_id(
    conn: asyncpg.Connection,
    comanda_id: str,
) -> Comanda | None:
    """Retorna una comanda por su ID, o None si no existe."""
    return await comanda_repository.get_comanda_por_id(conn, comanda_id)
