from uuid import UUID

import asyncpg

from app.exceptions import Conflicto, NoEncontrado
from app.repositories import metodos_pago_repository
from app.schemas.metodos_pago import MetodosPagoCreate, MetodosPagoOut, MetodosPagoUpdate


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[MetodosPagoOut]:
    rows = await metodos_pago_repository.listar(conn, sucursal_id)
    return [MetodosPagoOut.model_validate(r) for r in rows]


async def obtener(conn: asyncpg.Connection, metodo_pago_id: UUID) -> MetodosPagoOut:
    row = await metodos_pago_repository.obtener(conn, metodo_pago_id)
    if not row or not row["activo"]:
        raise NoEncontrado("Método de pago")
    return MetodosPagoOut.model_validate(row)


async def crear(conn: asyncpg.Connection, body: MetodosPagoCreate) -> MetodosPagoOut:
    if await metodos_pago_repository.nombre_existe(conn, body.nombre, body.sucursal_id):
        raise Conflicto(f"Ya existe un método de pago con el nombre '{body.nombre}'.")
    row = await metodos_pago_repository.crear(
        conn, sucursal_id=body.sucursal_id, nombre=body.nombre, descripcion=body.descripcion
    )
    return MetodosPagoOut.model_validate(row)


async def actualizar(
    conn: asyncpg.Connection, metodo_pago_id: UUID, body: MetodosPagoUpdate
) -> MetodosPagoOut:
    await obtener(conn, metodo_pago_id)
    updates = body.model_dump(exclude_unset=True)
    row = await metodos_pago_repository.actualizar(conn, metodo_pago_id, updates)
    if not row:
        raise NoEncontrado("Método de pago")
    return MetodosPagoOut.model_validate(row)


async def eliminar(conn: asyncpg.Connection, metodo_pago_id: UUID) -> None:
    await obtener(conn, metodo_pago_id)
    await metodos_pago_repository.eliminar(conn, metodo_pago_id)
