from uuid import UUID

import asyncpg

from app.exceptions import Conflicto, NoEncontrado
from app.repositories import metodos_pago as repo
from app.schemas.metodos_pago import MetodosPagoCreate, MetodosPagoOut, MetodosPagoUpdate


async def listar(conn: asyncpg.Connection) -> list[MetodosPagoOut]:
    rows = await repo.listar(conn)
    return [MetodosPagoOut.model_validate(dict(r)) for r in rows]


async def obtener(conn: asyncpg.Connection, metodo_pago_id: UUID) -> MetodosPagoOut:
    row = await repo.obtener_por_id(conn, metodo_pago_id)
    if not row or not row["activo"]:
        raise NoEncontrado("Método de pago")
    return MetodosPagoOut.model_validate(dict(row))


async def crear(
    conn: asyncpg.Connection, body: MetodosPagoCreate, actor_id: UUID | None = None
) -> MetodosPagoOut:
    try:
        row = await repo.crear(
            conn, nombre=body.nombre, descripcion=body.descripcion, creado_por=actor_id
        )
    except asyncpg.UniqueViolationError:
        raise Conflicto(f"Ya existe un método de pago con el nombre '{body.nombre}'.") from None
    return MetodosPagoOut.model_validate(dict(row))


async def actualizar(
    conn: asyncpg.Connection,
    metodo_pago_id: UUID,
    body: MetodosPagoUpdate,
    actor_id: UUID | None = None,
) -> MetodosPagoOut:
    actual = await obtener(conn, metodo_pago_id)
    cambios = body.model_dump(exclude_unset=True)
    if not cambios:
        return actual
    try:
        row = await repo.actualizar(conn, metodo_pago_id, cambios, modificado_por=actor_id)
    except asyncpg.UniqueViolationError:
        raise Conflicto("Ya existe un método de pago con ese nombre.") from None
    assert row is not None  # garantizado por obtener() previo
    return MetodosPagoOut.model_validate(dict(row))


async def eliminar(
    conn: asyncpg.Connection, metodo_pago_id: UUID, actor_id: UUID | None = None
) -> None:
    await obtener(conn, metodo_pago_id)
    await repo.desactivar(conn, metodo_pago_id, modificado_por=actor_id)
