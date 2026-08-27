"""
app/services/insumo_service.py
Lógica de negocio para insumos.
SAD §3.2: el service orquesta repositorios, nunca escribe SQL directamente.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg

from app.exceptions import DatosInvalidos, NoEncontrado
from app.repositories import (
    insumo_repository,
    producto_insumo_repository,
    proveedor_repository,
    unidad_medida_repository,
)
from app.schemas.auth import TokenData
from app.schemas.insumo import (
    InsumoAlertasOut,
    InsumoCrear,
    InsumoOut,
    InsumoRecetaInversaOut,
    InsumoUpdate,
)


async def _validar_unidades(
    conn: asyncpg.Connection, unidad_base_id: UUID, unidad_compra_id: UUID
) -> None:
    base = await unidad_medida_repository.obtener(conn, unidad_base_id)
    compra = await unidad_medida_repository.obtener(conn, unidad_compra_id)
    if not base or not compra:
        raise DatosInvalidos("La unidad base o la unidad de compra no existen.")
    if base["tipo"] != compra["tipo"]:
        raise DatosInvalidos(
            "La unidad base y la unidad de compra deben ser del mismo tipo "
            "(masa, volumen o pieza)."
        )


async def _validar_proveedor(
    conn: asyncpg.Connection, proveedor_id: UUID | None, sucursal_id: UUID
) -> None:
    if proveedor_id is None:
        return
    proveedor = await proveedor_repository.obtener(conn, proveedor_id)
    if not proveedor or proveedor["sucursal_id"] != sucursal_id:
        raise DatosInvalidos("El proveedor indicado no pertenece a esta sucursal.")


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[InsumoOut]:
    rows = await insumo_repository.listar(conn, sucursal_id)
    return [InsumoOut.model_validate(r) for r in rows]


async def listar_estimaciones(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> list[InsumoRecetaInversaOut]:
    rows = await producto_insumo_repository.listar_por_sucursal(conn, sucursal_id)
    return [InsumoRecetaInversaOut.model_validate(r) for r in rows]


async def listar_alertas(conn: asyncpg.Connection, sucursal_id: UUID) -> InsumoAlertasOut:
    rows = await insumo_repository.listar_bajo_umbral(conn, sucursal_id)
    criticos: list[InsumoOut] = []
    por_reordenar: list[InsumoOut] = []
    for r in rows:
        destino = criticos if r["stock_actual"] < r["stock_minimo"] else por_reordenar
        destino.append(InsumoOut.model_validate(r))
    return InsumoAlertasOut(criticos=criticos, por_reordenar=por_reordenar)


async def obtener(conn: asyncpg.Connection, insumo_id: UUID) -> InsumoOut:
    row = await insumo_repository.obtener(conn, insumo_id)
    if not row:
        raise NoEncontrado("Insumo")
    return InsumoOut.model_validate(row)


async def crear(conn: asyncpg.Connection, body: InsumoCrear, current_user: TokenData) -> InsumoOut:
    await _validar_unidades(conn, body.unidad_base_id, body.unidad_compra_id)
    await _validar_proveedor(conn, body.proveedor_principal_id, body.sucursal_id)
    row = await insumo_repository.crear(
        conn,
        sucursal_id=body.sucursal_id,
        nombre=body.nombre,
        descripcion=body.descripcion,
        unidad_base_id=body.unidad_base_id,
        unidad_compra_id=body.unidad_compra_id,
        stock_inicial=body.stock_inicial,
        stock_minimo=body.stock_minimo,
        costo_unitario=body.costo_unitario,
        proveedor_principal_id=body.proveedor_principal_id,
        creado_por=UUID(current_user.sub),
        punto_reorden=body.punto_reorden,
        stock_maximo=body.stock_maximo,
    )
    return InsumoOut.model_validate(row)


async def actualizar(
    conn: asyncpg.Connection,
    insumo_id: UUID,
    body: InsumoUpdate,
    current_user: TokenData,
) -> InsumoOut:
    actual = await obtener(conn, insumo_id)
    updates = body.model_dump(exclude_unset=True)
    if updates.get("proveedor_principal_id") is not None:
        await _validar_proveedor(conn, updates["proveedor_principal_id"], actual.sucursal_id)
    updates["modificado_por"] = UUID(current_user.sub)
    row = await insumo_repository.actualizar(conn, insumo_id, updates)
    if not row:
        raise NoEncontrado("Insumo")
    return InsumoOut.model_validate(row)


async def eliminar(conn: asyncpg.Connection, insumo_id: UUID) -> None:
    await obtener(conn, insumo_id)
    await insumo_repository.eliminar(conn, insumo_id)
