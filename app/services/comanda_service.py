"""
app/services/comanda_service.py
Lógica de negocio para comandas.
SAD §3.2: el service orquesta repositorios, nunca escribe SQL directamente.
"""

from __future__ import annotations

from dataclasses import asdict

from decimal import Decimal

import asyncpg

from app.core.ws_manager import manager
from app.models.comanda import Comanda
from app.repositories import comanda_repository, producto_repository
from app.schemas.auth import RoleEnum, TokenData
from app.schemas.comanda import ComandaCreate

VE_TODAS_LAS_SUCURSALES = None


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

async def crear_comanda(conn: asyncpg.Connection, comanda_in: ComandaCreate, creado_por: str | None = None) -> Comanda:
    """Crea una comanda con los combos desglosados y notifica."""

    detalles_expandidos = await expandir_detalles_comanda(conn, comanda_in.detalles_comanda)
    comanda = await comanda_repository.crear_comanda_con_detalles(
        conn, comanda_in, detalles_expandidos, creado_por
    )
    comanda.detalles = await expandir_detalles_comanda(conn, comanda.detalles)

    await manager.broadcast(
        comanda.sucursal_id, {"type": "comanda_creada", "comanda": asdict(comanda)}
    )
    return comanda

async def listar_pendientes(conn: asyncpg.Connection, current_user: TokenData) -> list[Comanda]:
    scope = sucursal_scope(current_user)
    comandas = await comanda_repository.get_comandas_pendientes(conn, scope)

    for comanda in comandas:
        comanda.detalles = await expandir_detalles_comanda(conn, comanda.detalles)
        
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
        await manager.broadcast(
            comanda.sucursal_id, {"type": "comanda_actualizada", "comanda": asdict(comanda)}
        )
    return comanda


async def obtener_por_id(
    conn: asyncpg.Connection,
    comanda_id: str,
) -> Comanda | None:
    """Retorna una comanda por su ID, o None si no existe."""
    return await comanda_repository.get_comanda_por_id(conn, comanda_id)

def _producto_id_de_detalle(item) -> str:
    if isinstance(item, dict):
        return str(item.get("producto_id") or item["id"])
    if hasattr(item, "producto_id") and hasattr(item, "comanda_id"):
        return str(item.producto_id)
    return str(item.id)


def _cantidad_de_detalle(item) -> int:
    return item["cantidad"] if isinstance(item, dict) else item.cantidad


def _notas_de_detalle(item) -> str | None:
    if isinstance(item, dict):
        return item.get("notas_especiales")
    return item.notas_especiales


def _detalle_a_dict(item, nombre: str) -> dict:
    if isinstance(item, dict):
        detalle = dict(item)
    elif hasattr(item, "model_dump"):
        detalle = item.model_dump()
    else:
        detalle = asdict(item)
    detalle["nombre"] = nombre
    if (
        Decimal(str(detalle.get("precio_unitario", 0))) == 0
        and Decimal(str(detalle.get("importe", detalle.get("subtotal", 0)))) == 0
        and not detalle.get("es_hijo_de")
    ):
        detalle["es_hijo_combo"] = True
    return detalle


async def expandir_detalles_comanda(conn, detalles: list) -> list[dict]:
    hijos_a_padres = await producto_repository.get_hijos_a_padres_map(conn)
    detalles_finales = []

    for item in detalles:
        producto_id = _producto_id_de_detalle(item)

        if await producto_repository.es_producto_combo(conn, producto_id):
            producto_padre = await producto_repository.get_by_id(conn, producto_id)
            nombre_padre = producto_padre["nombre"] if producto_padre else ""
            hijos = await producto_repository.get_combo_hijos(conn, producto_id)

            for hijo in hijos:
                hijo_producto = await producto_repository.get_by_id(conn, str(hijo["producto_id"]))
                nombre_hijo = hijo_producto["nombre"] if hijo_producto else ""
                detalles_finales.append({
                    "producto_id": str(hijo["producto_id"]),
                    "nombre": nombre_hijo,
                    "nombre_combo_padre": nombre_padre,
                    "cantidad": hijo["cantidad"] * _cantidad_de_detalle(item),
                    "precio_unitario": 0,
                    "subtotal": 0,
                    "es_hijo_de": producto_id,
                    "notas_especiales": _notas_de_detalle(item),
                })
        else:
            producto_info = await producto_repository.get_by_id(conn, producto_id)
            nombre_producto = producto_info["nombre"] if producto_info else ""
            detalle = _detalle_a_dict(item, nombre_producto)
            padre_nombre = hijos_a_padres.get(producto_id)
            if padre_nombre:
                detalle["nombre_combo_padre"] = padre_nombre
            detalles_finales.append(detalle)

    return detalles_finales