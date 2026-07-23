"""
app/services/comanda_service.py
Lógica de negocio para comandas.
SAD §3.2: el service orquesta repositorios, nunca escribe SQL directamente.
"""

from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

import asyncpg

from app.core.ws_manager import manager
from app.models.comanda import Comanda
from app.repositories import comanda_repository, combo_repository
from app.schemas.auth import RoleEnum, TokenData
from app.schemas.comanda import ComandaCreate

VE_TODAS_LAS_SUCURSALES = None


async def _adjuntar_items_combo(conn: asyncpg.Connection, comandas: list[Comanda]) -> None:
    """Adjunta a cada detalle de tipo combo el desglose de productos que lo
    integran (cantidad ya multiplicada por la cantidad de combos pedidos),
    para que cocina sepa exactamente que preparar."""
    for comanda in comandas:
        for detalle in comanda.detalles:
            if detalle.producto_tipo != "C":
                continue
            items = await combo_repository.obtener_items_de_combo(conn, UUID(detalle.producto_id))
            detalle.productos_combo = [
                {
                    "producto_id": str(item["producto_id"]),
                    "nombre": item["nombre"],
                    "cantidad": item["cantidad"] * detalle.cantidad,
                }
                for item in items
            ]


def sucursal_scope(current_user: TokenData) -> str | None:
    """Sucursal a la que debe limitarse current_user, o VE_TODAS_LAS_SUCURSALES
    (None) si el rol ve todas las sucursales (AdministradorSistema). Mismo
    criterio que branch_service.list_branches. Si el usuario no es
    AdministradorSistema y no tiene sucursal asignada, devuelve un id que no
    existe para que el filtro no traiga nada, en vez de reventar."""
    if current_user.role == RoleEnum.administrador_sistema:
        return VE_TODAS_LAS_SUCURSALES
    if current_user.branch_id is None:
        return "00000000-0000-0000-0000-000000000000"
    return str(current_user.branch_id)


async def crear_comanda(conn: asyncpg.Connection, comanda_in: ComandaCreate) -> Comanda:
    """Crea una comanda con sus detalles y notifica a los clientes conectados."""
    comanda = await comanda_repository.crear_comanda_con_detalles(conn, comanda_in)
    await _adjuntar_items_combo(conn, [comanda])
    await manager.broadcast(
        comanda.sucursal_id, {"type": "comanda_creada", "comanda": asdict(comanda)}
    )
    return comanda


async def listar_pendientes(conn: asyncpg.Connection, current_user: TokenData) -> list[Comanda]:
    """Retorna las comandas activas (estados P, E, L) de la sucursal de
    current_user, o de todas si es AdministradorSistema."""
    scope = sucursal_scope(current_user)
    comandas = await comanda_repository.get_comandas_pendientes(conn, scope)
    await _adjuntar_items_combo(conn, comandas)
    return comandas


async def cambiar_estado(
    conn: asyncpg.Connection,
    comanda_id: str,
    nuevo_estado: str,
) -> Comanda | None:
    """
    Actualiza el estado de una comanda y notifica a los clientes conectados.
    Retorna None si la comanda no existe.
    """
    comanda = await comanda_repository.actualizar_estado_comanda(conn, comanda_id, nuevo_estado)
    if comanda is not None:
        await _adjuntar_items_combo(conn, [comanda])
        await manager.broadcast(
            comanda.sucursal_id, {"type": "comanda_actualizada", "comanda": asdict(comanda)}
        )
    return comanda


async def obtener_por_id(
    conn: asyncpg.Connection,
    comanda_id: str,
) -> Comanda | None:
    """Retorna una comanda por su ID, o None si no existe."""
    comanda = await comanda_repository.get_comanda_por_id(conn, comanda_id)
    if comanda is not None:
        await _adjuntar_items_combo(conn, [comanda])
    return comanda
