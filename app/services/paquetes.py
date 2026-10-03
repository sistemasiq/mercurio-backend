from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado
from app.repositories import paquete_tipos_evento_repository, paquetes_repository
from app.schemas.paquetes import PaquetesCreate, PaquetesOut, PaquetesUpdate


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[PaquetesOut]:
    rows = await paquetes_repository.listar(conn, sucursal_id)
    resultado = []
    for row in rows:
        row_dict = dict(row)
        row_dict["productos_incluidos"] = await paquetes_repository.obtener_items_de_paquete(
            conn, row["id"]
        )
        row_dict["tipos_evento"] = await paquetes_repository.listar_tipos_evento_de_paquete(
            conn, row["id"]
        )
        resultado.append(PaquetesOut.model_validate(row_dict))
    return resultado


async def obtener(conn: asyncpg.Connection, paquete_id: UUID) -> PaquetesOut:
    row = await paquetes_repository.obtener(conn, paquete_id)
    if not row or not row["activo"]:
        raise NoEncontrado("Paquete")
    row_dict = dict(row)
    row_dict["productos_incluidos"] = await paquetes_repository.obtener_items_de_paquete(
        conn, paquete_id
    )
    row_dict["tipos_evento"] = await paquetes_repository.listar_tipos_evento_de_paquete(
        conn, paquete_id
    )
    return PaquetesOut.model_validate(row_dict)


async def crear(conn: asyncpg.Connection, body: PaquetesCreate) -> PaquetesOut:
    async with conn.transaction():
        row = await paquetes_repository.crear(
            conn,
            sucursal_id=body.sucursal_id,
            nombre=body.nombre,
            descripcion=body.descripcion,
            min_invitados=body.min_invitados,
            max_invitados=body.max_invitados,
            precio_base=body.precio_base,
            precio_hora_pulsera=body.precio_hora_pulsera,
            duracion_horas=body.duracion_horas,
            destacado=body.destacado,
            anticipo_porcentaje=body.anticipo_porcentaje,
        )
        if body.productos_incluidos:
            items_dict = [item.model_dump() for item in body.productos_incluidos]
            await paquetes_repository.asociar_productos_a_paquete(
                conn, paquete_id=row["id"], items=items_dict
            )
    return await obtener(conn, row["id"])


async def duplicar(conn: asyncpg.Connection, paquete_id: UUID, usuario_id: UUID) -> PaquetesOut:
    """Copia un paquete, sus productos incluidos y sus tipos de evento, con
    el nombre '<original> (copia)'."""
    original = await paquetes_repository.obtener(conn, paquete_id)
    if not original or not original["activo"]:
        raise NoEncontrado("Paquete")

    incluidos = await paquetes_repository.obtener_items_de_paquete(conn, paquete_id)
    tipos_evento = await paquetes_repository.listar_tipos_evento_de_paquete(conn, paquete_id)

    async with conn.transaction():
        nuevo = await paquetes_repository.crear(
            conn,
            sucursal_id=original["sucursal_id"],
            nombre=f"{original['nombre']} (copia)",
            descripcion=original["descripcion"],
            min_invitados=original["min_invitados"],
            max_invitados=original["max_invitados"],
            precio_base=original["precio_base"],
            precio_hora_pulsera=original["precio_hora_pulsera"],
            duracion_horas=original["duracion_horas"],
            destacado=original["destacado"],
            anticipo_porcentaje=original["anticipo_porcentaje"],
        )
        if incluidos:
            items_dict = [
                {"producto_id": item["producto_id"], "cantidad": item["cantidad"]}
                for item in incluidos
            ]
            await paquetes_repository.asociar_productos_a_paquete(
                conn, paquete_id=nuevo["id"], items=items_dict, usuario_id=usuario_id
            )
        for tipo in tipos_evento:
            await paquete_tipos_evento_repository.agregar(conn, nuevo["id"], tipo["id"])

    return await obtener(conn, nuevo["id"])


async def actualizar(
    conn: asyncpg.Connection, paquete_id: UUID, body: PaquetesUpdate
) -> PaquetesOut:
    await obtener(conn, paquete_id)
    updates = body.model_dump(exclude_unset=True)
    productos_incluidos = updates.pop("productos_incluidos", None)

    async with conn.transaction():
        row = await paquetes_repository.actualizar(conn, paquete_id, updates)
        if not row:
            raise NoEncontrado("Paquete")

        if productos_incluidos is not None:
            await paquetes_repository.desasociar_todos_los_productos_de_paquete(conn, paquete_id)
            if productos_incluidos:
                await paquetes_repository.asociar_productos_a_paquete(
                    conn, paquete_id=paquete_id, items=productos_incluidos
                )

    return await obtener(conn, paquete_id)


async def eliminar(conn: asyncpg.Connection, paquete_id: UUID) -> None:
    await obtener(conn, paquete_id)
    await paquetes_repository.eliminar(conn, paquete_id)
