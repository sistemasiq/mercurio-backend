"""
app/services/presentacion_insumo_service.py
Lógica de negocio para presentaciones de compra de un insumo.
SAD §3.2: el service orquesta repositorios, nunca escribe SQL directamente.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado
from app.repositories import insumo_repository, presentacion_insumo_repository
from app.schemas.auth import TokenData
from app.schemas.presentacion_insumo import PresentacionCrear, PresentacionOut, PresentacionUpdate


async def listar(conn: asyncpg.Connection, insumo_id: UUID) -> list[PresentacionOut]:
    rows = await presentacion_insumo_repository.listar_por_insumo(conn, insumo_id)
    return [PresentacionOut.model_validate(r) for r in rows]


async def crear(
    conn: asyncpg.Connection,
    insumo_id: UUID,
    body: PresentacionCrear,
    current_user: TokenData,
) -> PresentacionOut:
    insumo = await insumo_repository.obtener(conn, insumo_id)
    if not insumo:
        raise NoEncontrado("Insumo")
    row = await presentacion_insumo_repository.crear(
        conn, insumo_id, body.nombre, body.equivalencia_base, UUID(current_user.sub)
    )
    return PresentacionOut.model_validate(row)


async def actualizar(
    conn: asyncpg.Connection,
    presentacion_id: UUID,
    body: PresentacionUpdate,
    current_user: TokenData,
) -> PresentacionOut:
    actual = await presentacion_insumo_repository.obtener(conn, presentacion_id)
    if not actual:
        raise NoEncontrado("Presentación")
    updates = body.model_dump(exclude_unset=True)
    updates["modificado_por"] = UUID(current_user.sub)
    row = await presentacion_insumo_repository.actualizar(conn, presentacion_id, updates)
    if not row:
        raise NoEncontrado("Presentación")
    return PresentacionOut.model_validate(row)


async def eliminar(conn: asyncpg.Connection, presentacion_id: UUID) -> None:
    actual = await presentacion_insumo_repository.obtener(conn, presentacion_id)
    if not actual:
        raise NoEncontrado("Presentación")
    await presentacion_insumo_repository.eliminar(conn, presentacion_id)
