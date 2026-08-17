"""
app/services/comanda_service.py
Lógica de negocio para comandas.
SAD §3.2: el service orquesta repositorios, nunca escribe SQL directamente.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, cast
from uuid import UUID

import asyncpg

from app.core.scope import sucursal_scope
from app.core.ws_manager import manager
from app.models.comanda import Comanda, DetalleComanda
from app.repositories import comanda_repository, producto_repository
from app.repositories.caja_repository import registrar_movimiento_caja
from app.schemas.auth import TokenData
from app.schemas.comanda import ComandaCreate
from app.services import inventario_service, lealtad_service


def _producto_id_de_detalle(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("producto_id") or item["id"])
    if hasattr(item, "producto_id") and hasattr(item, "comanda_id"):
        return str(item.producto_id)
    return str(item.id)


def _cantidad_de_detalle(item: Any) -> int:
    return int(item["cantidad"]) if isinstance(item, dict) else int(item.cantidad)


def _detalle_a_dict(item: Any, nombre: str) -> dict[str, Any]:
    if isinstance(item, dict):
        detalle = dict(item)
    elif hasattr(item, "model_dump"):
        detalle = item.model_dump()
    else:
        detalle = asdict(item)
    detalle["nombre"] = nombre
    return detalle


async def expandir_detalles_comanda(
    conn: asyncpg.Connection, detalles: list[Any]
) -> list[DetalleComanda | dict[str, Any]]:
    """Convierte los detalles con combos en detalles individuales (uno por
    producto hijo), para que cocina sepa exactamente qué preparar."""
    detalles_finales: list[DetalleComanda | dict[str, Any]] = []

    # Pre-computar: ¿qué combos ya tienen hijos en la lista?
    hijos_existentes = set()
    for d in detalles:
        padre = getattr(d, "es_hijo_de", None) or (
            d.get("es_hijo_de") if isinstance(d, dict) else None
        )
        if padre:
            hijos_existentes.add(padre)

    for item in detalles:
        producto_id = _producto_id_de_detalle(item)

        if await producto_repository.es_producto_combo(conn, producto_id):
            if producto_id in hijos_existentes:
                continue
            else:
                producto_padre = await producto_repository.get_by_id(conn, producto_id)
                nombre_padre = producto_padre["nombre"] if producto_padre else ""
                hijos = await producto_repository.get_combo_hijos(conn, producto_id)

                for hijo in hijos:
                    h_id = str(hijo["producto_id"])
                    hijo_producto = await producto_repository.get_by_id(conn, h_id)
                    nombre_hijo = hijo_producto["nombre"] if hijo_producto else ""
                    detalles_finales.append(
                        {
                            "producto_id": str(hijo["producto_id"]),
                            "nombre": nombre_hijo,
                            "nombre_combo_padre": nombre_padre,
                            "cantidad": hijo["cantidad"] * _cantidad_de_detalle(item),
                            "precio_unitario": 0,
                            "subtotal": 0,
                            "es_hijo_de": producto_id,
                            "es_hijo_combo": True,
                            "notas_especiales": None,
                        }
                    )
        else:
            producto_info = await producto_repository.get_by_id(conn, producto_id)
            nombre_producto = producto_info["nombre"] if producto_info else ""
            detalle = _detalle_a_dict(item, nombre_producto)

            # Un ítem pertenece a un combo SOLO si la orden lo trajo así
            # (campos persistidos es_hijo_de/nombre_combo_padre/es_hijo_combo).
            # Nunca se infiere desde el catálogo global de combos: un producto
            # que es integrante de un combo pero se vendió suelto debe salir
            # limpio, sin etiquetas de paquete que no le corresponden.
            if not detalle.get("nombre_combo_padre"):
                detalle["nombre_combo_padre"] = None
                detalle["es_hijo_de"] = None
                detalle["es_hijo_combo"] = False

            detalles_finales.append(detalle)

    return detalles_finales


async def crear_comanda(
    conn: asyncpg.Connection,
    comanda_in: ComandaCreate,
    current_user: TokenData,
    apertura_caja_id: str,
) -> Comanda:
    """Crea una comanda, descuenta el stock de los insumos de la receta de
    cada producto vendido (aborta todo si alguno no alcanza), registra el
    movimiento de venta en la caja del turno activo, la reexpande desde BD
    y notifica a los clientes conectados.

    metodo_pago_id va en None temporalmente: el módulo de métodos de pago para
    comandas todavía no está integrado (columna nullable a propósito mientras tanto).
    """
    creado_por = str(UUID(current_user.sub))

    async with conn.transaction():
        comanda = await comanda_repository.crear_comanda_con_detalles(
            conn, comanda_in, None, creado_por
        )
        await inventario_service.descontar_por_venta(
            conn,
            str(comanda_in.sucursal_id),
            comanda_in.detalles_comanda,
            comanda.id,
            UUID(current_user.sub),
        )
        await registrar_movimiento_caja(
            conn,
            apertura_caja_id=apertura_caja_id,
            tipo_movimiento="O",
            referencia_id=comanda.id,
            metodo_pago_id=None,
            monto=comanda.total_final,
            creado_por=creado_por,
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
    current_user: TokenData,
    motivo_cancelacion: str | None = None,
) -> Comanda | None:
    """
    Actualiza el estado de una comanda y notifica a los clientes conectados.
    Registra auditoría (modificado, modificado_por). Si nuevo_estado == 'C'
    (y no lo estaba ya, para no revertir dos veces), desactiva la comanda,
    requiere motivo_cancelacion y revierte el stock que se descontó al
    crearla. Retorna None si la comanda no existe.
    """
    usuario_id = str(UUID(current_user.sub))
    anterior = await comanda_repository.get_comanda_por_id(conn, comanda_id)
    if anterior is None:
        return None

    es_cancelacion = nuevo_estado == "C" and anterior.estado_actual != "C"

    async with conn.transaction():
        comanda = await comanda_repository.actualizar_estado_comanda(
            conn,
            comanda_id,
            nuevo_estado,
            usuario_id,
            motivo_cancelacion=motivo_cancelacion,
            desactivar=es_cancelacion,
        )
        if comanda is not None and es_cancelacion:
            # anterior viene directo de get_comanda_por_id, antes de pasar por
            # expandir_detalles_comanda — siempre son DetalleComanda, nunca dicts.
            detalles_anteriores = cast(list[DetalleComanda], anterior.detalles)
            await inventario_service.revertir_por_cancelacion(
                conn, anterior.sucursal_id, detalles_anteriores, comanda_id, UUID(current_user.sub)
            )
            await lealtad_service.revertir_por_cancelacion(
                conn, UUID(comanda_id), UUID(current_user.sub)
            )

    if comanda is not None:
        comanda.detalles = await expandir_detalles_comanda(conn, comanda.detalles)
        await manager.broadcast(
            comanda.sucursal_id, {"type": "comanda_actualizada", "comanda": asdict(comanda)}
        )
    return comanda


async def modificar_comanda_parcial(
    conn: asyncpg.Connection,
    comanda_id: str,
    detalles_ids_a_eliminar: list[str],
    usuario_id: str | None = None,
    motivo_cancelacion: str | None = None,
) -> Comanda | None:
    """Elimina productos de una comanda en estado 'P' y recalcula el total.

    Si se eliminan todos los productos, cancela automáticamente la comanda
    y requiere motivo_cancelacion.

    Retorna None si la comanda no existe o no está en estado 'P'.
    Notifica a cocina vía WebSocket después de la modificación.
    """
    comanda = await comanda_repository.modificar_comanda_parcial(
        conn,
        comanda_id,
        detalles_ids_a_eliminar,
        usuario_id,
        motivo_cancelacion,
    )
    if comanda is not None:
        comanda.detalles = await expandir_detalles_comanda(conn, comanda.detalles)
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
