"""
app/services/compra_service.py
Lógica de negocio para compras a proveedor. Al recibir una compra convierte
cada línea a la unidad base del insumo y genera movimientos de entrada
(fase 3). SAD §3.2: el service orquesta repositorios, nunca escribe SQL
directamente.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

from app.exceptions import Conflicto, DatosInvalidos, NoEncontrado
from app.repositories import (
    compra_repository,
    insumo_repository,
    movimiento_inventario_repository,
    presentacion_insumo_repository,
    proveedor_repository,
    unidad_medida_repository,
)
from app.schemas.compra import (
    CompraCrear,
    CompraEditar,
    CompraOut,
    CompraUpdate,
    RecibirCompraRequest,
)
from app.services import costeo_service


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


async def _validar_y_calcular_base(
    conn: asyncpg.Connection,
    insumo: dict[str, Any],
    unidad_medida_id: UUID | None,
    presentacion_id: UUID | None,
    cantidad: Decimal,
    costo_unitario: Decimal,
) -> tuple[Decimal, Decimal]:
    """Valida la línea y devuelve (cantidad_base, costo_base) expresados en
    la unidad_base_id del insumo. Se bifurca según cuál campo trae la línea:
    unidad_medida_id (factor global entre unidades) o presentacion_id
    (equivalencia directa y específica del insumo, fase 7)."""
    if presentacion_id is not None:
        presentacion = await presentacion_insumo_repository.obtener(conn, presentacion_id)
        if not presentacion:
            raise DatosInvalidos("La presentación indicada no existe.")
        if presentacion["insumo_id"] != insumo["id"] or not presentacion["activo"]:
            raise DatosInvalidos(
                f"La presentación indicada no pertenece a «{insumo['nombre']}» o está inactiva."
            )
        equivalencia = presentacion["equivalencia_base"]
        return cantidad * equivalencia, costo_unitario / equivalencia

    assert unidad_medida_id is not None
    await _validar_unidad_compatible(conn, unidad_medida_id, insumo)
    unidad_linea = await unidad_medida_repository.obtener(conn, unidad_medida_id)
    unidad_base = await unidad_medida_repository.obtener(conn, insumo["unidad_base_id"])
    assert unidad_linea is not None and unidad_base is not None
    factor = unidad_linea["factor_a_base"] / unidad_base["factor_a_base"]
    return cantidad * factor, costo_unitario / factor


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
        await _validar_y_calcular_base(
            conn,
            insumo,
            detalle.unidad_medida_id,
            detalle.presentacion_id,
            detalle.cantidad,
            detalle.costo_unitario,
        )

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


async def editar(conn: asyncpg.Connection, compra_id: UUID, body: CompraEditar) -> CompraOut:
    """Reemplaza proveedor, notas y líneas de una compra que sigue en 'P'."""
    compra = await compra_repository.obtener(conn, compra_id)
    if not compra:
        raise NoEncontrado("Compra")
    if compra["estado"] != "P":
        raise Conflicto("Solo se puede editar una compra pendiente.")

    proveedor = await proveedor_repository.obtener(conn, body.proveedor_id)
    if not proveedor or proveedor["sucursal_id"] != compra["sucursal_id"]:
        raise DatosInvalidos("El proveedor no pertenece a esta sucursal.")
    for detalle in body.detalles:
        insumo = await insumo_repository.obtener(conn, detalle.insumo_id)
        if not insumo:
            raise NoEncontrado("Insumo")
        if insumo["sucursal_id"] != compra["sucursal_id"]:
            raise DatosInvalidos("El insumo no pertenece a esta sucursal.")
        await _validar_y_calcular_base(
            conn,
            insumo,
            detalle.unidad_medida_id,
            detalle.presentacion_id,
            detalle.cantidad,
            detalle.costo_unitario,
        )

    await compra_repository.reemplazar_detalles(conn, compra_id, body)
    return await obtener(conn, compra_id)


async def recibir(
    conn: asyncpg.Connection,
    compra_id: UUID,
    creado_por: UUID,
    body: RecibirCompraRequest | None = None,
) -> CompraOut:
    compra = await compra_repository.obtener(conn, compra_id)
    if not compra:
        raise NoEncontrado("Compra")
    if compra["estado"] not in ("P", "PARCIAL"):
        raise Conflicto("La compra ya fue recibida o está cancelada.")

    detalles = await compra_repository.listar_detalles(conn, compra_id)
    solicitado: dict[str, Decimal] = {}
    if body and body.lineas:
        solicitado = {str(linea.detalle_id): linea.cantidad for linea in body.lineas}

    async with conn.transaction():
        algo_recibido = False
        for detalle in detalles:
            pendiente = detalle["cantidad"] - detalle["cantidad_recibida"]
            if pendiente <= 0:
                continue
            cantidad = solicitado.get(str(detalle["id"]), pendiente) if solicitado else pendiente
            recibir_ahora = min(cantidad, pendiente)
            if recibir_ahora <= 0:
                continue
            algo_recibido = True

            insumo = await insumo_repository.obtener(conn, detalle["insumo_id"])
            if not insumo:
                raise NoEncontrado("Insumo")
            cantidad_base, costo_base = await _validar_y_calcular_base(
                conn,
                insumo,
                detalle["unidad_medida_id"],
                detalle["presentacion_id"],
                recibir_ahora,
                detalle["costo_unitario"],
            )
            nuevo_stock = await insumo_repository.ajustar_stock(
                conn, detalle["insumo_id"], cantidad_base
            )
            if nuevo_stock is None:
                raise RuntimeError("No se pudo aumentar el stock del insumo al recibir la compra")
            await costeo_service.registrar_entrada(
                conn, detalle["insumo_id"], cantidad_base, costo_base, "compra", compra_id
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
                costo_total=cantidad_base * costo_base,
            )
            await compra_repository.sumar_recepcion_linea(conn, detalle["id"], recibir_ahora)

        if not algo_recibido:
            raise Conflicto("No hay nada pendiente por recibir en esta compra.")

        detalles = await compra_repository.listar_detalles(conn, compra_id)
        completa = all(d["cantidad_recibida"] >= d["cantidad"] for d in detalles)
        actualizada = await compra_repository.marcar_estado(
            conn, compra_id, "R" if completa else "PARCIAL"
        )
        if actualizada is None:
            raise Conflicto("La compra ya fue recibida o está cancelada.")

    return await _construir_out(conn, actualizada)


async def cancelar(conn: asyncpg.Connection, compra_id: UUID) -> CompraOut:
    compra = await compra_repository.obtener(conn, compra_id)
    if not compra:
        raise NoEncontrado("Compra")
    if compra["estado"] != "P":
        raise Conflicto("Solo se puede cancelar una compra pendiente sin recepciones.")
    cancelada = await compra_repository.marcar_cancelada(conn, compra_id)
    if cancelada is None:
        raise Conflicto("La compra ya fue recibida o está cancelada.")
    return await _construir_out(conn, cancelada)
