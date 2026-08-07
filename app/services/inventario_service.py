"""
app/services/inventario_service.py
Descuento/reversión automática de stock al vender, y ajustes manuales
(entrada manual, merma). SAD §3.2: el service orquesta repositorios, nunca
escribe SQL directamente.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado, StockInsuficienteError
from app.models.comanda import DetalleComanda
from app.repositories import (
    combo_repository,
    insumo_repository,
    movimiento_inventario_repository,
    producto_insumo_repository,
    producto_repository,
)
from app.schemas.comanda import DetalleCreate
from app.schemas.movimiento_inventario import MovimientoInventarioOut, MovimientoManualCreate


async def _consumo_insumos(
    conn: asyncpg.Connection,
    producto_id: UUID,
    cantidad_vendida: int,
    tipo: str | None = None,
) -> list[dict[str, Any]]:
    """Insumos y cantidad a mover para vender/revertir `cantidad_vendida`
    unidades de un producto. Los combos ('C') no tienen producto_insumos
    propio — se expanden a los productos que lo integran (un solo nivel,
    igual que _adjuntar_items_combo en comanda_service.py) y se suma la
    receta de cada uno."""
    if tipo is None:
        producto = await producto_repository.obtener(conn, producto_id)
        tipo = producto.tipo if producto else None

    if tipo == "C":
        resultado: list[dict[str, Any]] = []
        for item in await combo_repository.obtener_items_de_combo(conn, producto_id):
            sub_cantidad = item["cantidad"] * cantidad_vendida
            for r in await producto_insumo_repository.listar_por_producto(
                conn, item["producto_id"]
            ):
                resultado.append(
                    {
                        "insumo_id": r["insumo_id"],
                        "insumo_nombre": r["insumo_nombre"],
                        "consumo": r["cantidad"] * sub_cantidad,
                    }
                )
        return resultado

    return [
        {
            "insumo_id": r["insumo_id"],
            "insumo_nombre": r["insumo_nombre"],
            "consumo": r["cantidad"] * cantidad_vendida,
        }
        for r in await producto_insumo_repository.listar_por_producto(conn, producto_id)
    ]


async def descontar_por_venta(
    conn: asyncpg.Connection,
    sucursal_id: str,
    detalles: list[DetalleCreate],
    comanda_id: str,
    creado_por: UUID,
) -> None:
    """Descuenta del stock los insumos de la receta de cada producto vendido
    (expandiendo combos a sus productos integrantes). Lanza
    StockInsuficienteError si algún insumo no alcanza — el llamador debe
    envolver esto en una transacción para que aborte la comanda completa.

    Los detalles con es_hijo_combo=True son líneas informativas que el
    FrontEnd agrega para mostrar el contenido de un combo (cocina/ticket) --
    no representan una venta independiente. La línea del combo padre (tipo
    'C') ya se expande más abajo a la receta de cada uno de sus integrantes,
    así que procesar también las líneas hijas descontaría cada insumo del
    combo dos veces."""
    for detalle in detalles:
        if detalle.es_hijo_combo:
            continue
        for item in await _consumo_insumos(conn, UUID(detalle.id), detalle.cantidad):
            nuevo_stock = await insumo_repository.ajustar_stock(
                conn, item["insumo_id"], -item["consumo"]
            )
            if nuevo_stock is None:
                raise StockInsuficienteError(item["insumo_nombre"], "completar la venta")
            await movimiento_inventario_repository.registrar(
                conn,
                sucursal_id=UUID(sucursal_id),
                insumo_id=item["insumo_id"],
                tipo="S",
                cantidad=item["consumo"],
                stock_resultante=nuevo_stock,
                motivo="venta_comanda",
                referencia_id=UUID(comanda_id),
                notas=None,
                creado_por=creado_por,
            )


async def revertir_por_cancelacion(
    conn: asyncpg.Connection,
    sucursal_id: str,
    detalles: list[DetalleComanda],
    comanda_id: str,
    creado_por: UUID,
) -> None:
    """Revierte (suma de vuelta) el stock descontado por una comanda cancelada.

    Igual que en descontar_por_venta, las líneas es_hijo_combo=True se
    omiten: nunca se les descontó stock propio (ver descontar_por_venta),
    así que tampoco se les debe revertir."""
    for detalle in detalles:
        if detalle.es_hijo_combo:
            continue
        items = await _consumo_insumos(
            conn, UUID(detalle.producto_id), detalle.cantidad, tipo=detalle.producto_tipo
        )
        for item in items:
            nuevo_stock = await insumo_repository.ajustar_stock(
                conn, item["insumo_id"], item["consumo"]
            )
            if nuevo_stock is None:
                # No debería pasar (estamos sumando) — no bloquear la cancelación por esto.
                continue
            await movimiento_inventario_repository.registrar(
                conn,
                sucursal_id=UUID(sucursal_id),
                insumo_id=item["insumo_id"],
                tipo="A",
                cantidad=item["consumo"],
                stock_resultante=nuevo_stock,
                motivo="cancelacion_comanda",
                referencia_id=UUID(comanda_id),
                notas=None,
                creado_por=creado_por,
            )


async def registrar_ajuste_manual(
    conn: asyncpg.Connection,
    insumo_id: UUID,
    body: MovimientoManualCreate,
    creado_por: UUID,
) -> MovimientoInventarioOut:
    insumo = await insumo_repository.obtener(conn, insumo_id)
    if not insumo:
        raise NoEncontrado("Insumo")
    delta = body.cantidad if body.tipo == "E" else -body.cantidad
    nuevo_stock = await insumo_repository.ajustar_stock(conn, insumo_id, delta)
    if nuevo_stock is None:
        raise StockInsuficienteError(insumo["nombre"], "registrar esta merma")
    motivo = "entrada_manual" if body.tipo == "E" else "merma"
    movimiento_id = await movimiento_inventario_repository.registrar(
        conn,
        sucursal_id=insumo["sucursal_id"],
        insumo_id=insumo_id,
        tipo=body.tipo,
        cantidad=body.cantidad,
        stock_resultante=nuevo_stock,
        motivo=motivo,
        referencia_id=None,
        notas=body.notas,
        creado_por=creado_por,
    )
    row = await movimiento_inventario_repository.obtener(conn, movimiento_id)
    if not row:
        raise RuntimeError("Error al recuperar el movimiento recién registrado")
    return MovimientoInventarioOut.model_validate(row)


async def listar_movimientos(
    conn: asyncpg.Connection,
    insumo_id: UUID,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[MovimientoInventarioOut]:
    rows = await movimiento_inventario_repository.listar_por_insumo(conn, insumo_id, desde, hasta)
    return [MovimientoInventarioOut.model_validate(r) for r in rows]
