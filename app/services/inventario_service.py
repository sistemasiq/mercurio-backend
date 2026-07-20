"""
app/services/inventario_service.py
Descuento/reversión automática de stock al vender, y ajustes manuales
(entrada manual, merma). SAD §3.2: el service orquesta repositorios, nunca
escribe SQL directamente.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado, StockInsuficienteError
from app.models.comanda import DetalleComanda
from app.repositories import (
    insumo_repository,
    movimiento_inventario_repository,
    producto_insumo_repository,
)
from app.schemas.comanda import DetalleCreate
from app.schemas.movimiento_inventario import MovimientoInventarioOut, MovimientoManualCreate


async def descontar_por_venta(
    conn: asyncpg.Connection,
    sucursal_id: str,
    detalles: list[DetalleCreate],
    comanda_id: str,
    creado_por: UUID,
) -> None:
    """Descuenta del stock los insumos de la receta de cada producto vendido.
    Lanza StockInsuficienteError si algún insumo no alcanza — el llamador
    debe envolver esto en una transacción para que aborte la comanda completa."""
    for detalle in detalles:
        receta = await producto_insumo_repository.listar_por_producto(conn, UUID(detalle.id))
        for item in receta:
            consumo = item["cantidad"] * detalle.cantidad
            nuevo_stock = await insumo_repository.ajustar_stock(conn, item["insumo_id"], -consumo)
            if nuevo_stock is None:
                raise StockInsuficienteError(item["insumo_nombre"], "completar la venta")
            await movimiento_inventario_repository.registrar(
                conn,
                sucursal_id=UUID(sucursal_id),
                insumo_id=item["insumo_id"],
                tipo="S",
                cantidad=consumo,
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
    """Revierte (suma de vuelta) el stock descontado por una comanda cancelada."""
    for detalle in detalles:
        receta = await producto_insumo_repository.listar_por_producto(
            conn, UUID(detalle.producto_id)
        )
        for item in receta:
            consumo = item["cantidad"] * detalle.cantidad
            nuevo_stock = await insumo_repository.ajustar_stock(conn, item["insumo_id"], consumo)
            if nuevo_stock is None:
                # No debería pasar (estamos sumando) — no bloquear la cancelación por esto.
                continue
            await movimiento_inventario_repository.registrar(
                conn,
                sucursal_id=UUID(sucursal_id),
                insumo_id=item["insumo_id"],
                tipo="A",
                cantidad=consumo,
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
    conn: asyncpg.Connection, insumo_id: UUID
) -> list[MovimientoInventarioOut]:
    rows = await movimiento_inventario_repository.listar_por_insumo(conn, insumo_id)
    return [MovimientoInventarioOut.model_validate(r) for r in rows]
