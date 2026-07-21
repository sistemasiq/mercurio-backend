"""
app/services/compra_service.py
Lógica de negocio para compras a proveedor. Al recibir una compra convierte
cada línea a la unidad base del insumo y genera movimientos de entrada
(fase 3). SAD §3.2: el service orquesta repositorios, nunca escribe SQL
directamente.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import asyncpg

from app.exceptions import Conflicto, DatosInvalidos, NoEncontrado
from app.repositories import (
    compra_repository,
    insumo_repository,
    movimiento_inventario_repository,
    proveedor_repository,
    unidad_medida_repository,
)
from app.schemas.compra import CompraCrear, CompraOut, CompraUpdate


async def _construir_out(conn: asyncpg.Connection, compra: dict[str, Any]) -> CompraOut:
    detalles = await compra_repository.listar_detalles(conn, compra["id"])
    return CompraOut.model_validate({**compra, "detalles": detalles})


async def _validar_unidad_compatible(
    conn: asyncpg.Connection, unidad_medida_id: UUID, insumo: dict[str, Any]
) -> None:
    unidad_linea = await unidad_medida_repository.obtener(conn, unidad_medida_id)
    unidad_base = await unidad_medida_repository.obtener(conn, insumo["unidad_base_id"])
    if not unidad_linea or not unidad_base:
        raise DatosInvalidos("Unidad de medida inválida.")
    if unidad_linea["tipo"] != unidad_base["tipo"]:
        raise DatosInvalidos(
            f"La unidad de la línea no es compatible con la unidad base de «{insumo['nombre']}»."
        )


async def crear(conn: asyncpg.Connection, body: CompraCrear, creado_por: UUID) -> CompraOut:
    proveedor = await proveedor_repository.obtener(conn, body.proveedor_id)
    if not proveedor:
        raise NoEncontrado("Proveedor")
    if proveedor["sucursal_id"] != body.sucursal_id:
        raise DatosInvalidos("El proveedor no pertenece a esta sucursal.")

    for detalle in body.detalles:
        insumo = await insumo_repository.obtener(conn, detalle.insumo_id)
        if not insumo:
            raise NoEncontrado("Insumo")
        if insumo["sucursal_id"] != body.sucursal_id:
            raise DatosInvalidos("El insumo no pertenece a esta sucursal.")
        await _validar_unidad_compatible(conn, detalle.unidad_medida_id, insumo)

    compra_id = await compra_repository.crear_con_detalles(
        conn, body.sucursal_id, body.proveedor_id, body.notas, body.detalles, creado_por
    )
    return await obtener(conn, compra_id)


async def obtener(conn: asyncpg.Connection, compra_id: UUID) -> CompraOut:
    row = await compra_repository.obtener(conn, compra_id)
    if not row:
        raise NoEncontrado("Compra")
    return await _construir_out(conn, row)


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[CompraOut]:
    rows = await compra_repository.listar(conn, sucursal_id)
    return [CompraOut.model_validate(r) for r in rows]


async def actualizar(conn: asyncpg.Connection, compra_id: UUID, body: CompraUpdate) -> CompraOut:
    await obtener(conn, compra_id)
    updates = body.model_dump(exclude_unset=True)
    row = await compra_repository.actualizar(conn, compra_id, updates)
    if not row:
        raise NoEncontrado("Compra")
    return await _construir_out(conn, row)


async def recibir(conn: asyncpg.Connection, compra_id: UUID, creado_por: UUID) -> CompraOut:
    compra = await compra_repository.obtener(conn, compra_id)
    if not compra:
        raise NoEncontrado("Compra")
    if compra["estado"] != "P":
        raise Conflicto("La compra ya fue recibida o está cancelada.")

    detalles = await compra_repository.listar_detalles(conn, compra_id)
    async with conn.transaction():
        for detalle in detalles:
            insumo = await insumo_repository.obtener(conn, detalle["insumo_id"])
            if not insumo:
                raise NoEncontrado("Insumo")
            await _validar_unidad_compatible(conn, detalle["unidad_medida_id"], insumo)

            unidad_linea = await unidad_medida_repository.obtener(conn, detalle["unidad_medida_id"])
            unidad_base = await unidad_medida_repository.obtener(conn, insumo["unidad_base_id"])
            assert unidad_linea is not None and unidad_base is not None
            factor = unidad_linea["factor_a_base"] / unidad_base["factor_a_base"]
            cantidad_base = detalle["cantidad"] * factor
            costo_base = detalle["costo_unitario"] / factor

            nuevo_stock = await insumo_repository.ajustar_stock(
                conn, detalle["insumo_id"], cantidad_base
            )
            if nuevo_stock is None:
                raise RuntimeError("No se pudo aumentar el stock del insumo al recibir la compra")
            await insumo_repository.actualizar(
                conn, detalle["insumo_id"], {"costo_unitario": costo_base}
            )
            await movimiento_inventario_repository.registrar(
                conn,
                sucursal_id=compra["sucursal_id"],
                insumo_id=detalle["insumo_id"],
                tipo="E",
                cantidad=cantidad_base,
                stock_resultante=nuevo_stock,
                motivo="compra",
                referencia_id=compra_id,
                notas=None,
                creado_por=creado_por,
            )

        marcada = await compra_repository.marcar_recibida(conn, compra_id)
        if marcada is None:
            raise Conflicto("La compra ya fue recibida o está cancelada.")

    return await _construir_out(conn, marcada)


async def cancelar(conn: asyncpg.Connection, compra_id: UUID) -> CompraOut:
    compra = await compra_repository.obtener(conn, compra_id)
    if not compra:
        raise NoEncontrado("Compra")
    if compra["estado"] != "P":
        raise Conflicto("La compra ya fue recibida o está cancelada.")
    cancelada = await compra_repository.marcar_cancelada(conn, compra_id)
    if cancelada is None:
        raise Conflicto("La compra ya fue recibida o está cancelada.")
    return await _construir_out(conn, cancelada)
