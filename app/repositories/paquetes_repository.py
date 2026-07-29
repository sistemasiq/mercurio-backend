from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

_SELECT = """
    SELECT id, sucursal_id, nombre, descripcion, personas_incluidas,
           precio_base, precio_persona_extra, precio_hora, activo, creado, creado_por,
           modificado, modificado_por
    FROM paquetes
"""

_RETURNING = """
    id, sucursal_id, nombre, descripcion, personas_incluidas,
    precio_base, precio_persona_extra, precio_hora, activo, creado, creado_por,
    modificado, modificado_por
"""


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[dict[str, Any]]:
    if sucursal_id:
        rows = await conn.fetch(_SELECT + " WHERE activo = TRUE AND sucursal_id = $1", sucursal_id)
    else:
        rows = await conn.fetch(_SELECT + " WHERE activo = TRUE")
    return [dict(r) for r in rows]


async def obtener(conn: asyncpg.Connection, paquete_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(_SELECT + " WHERE id = $1", paquete_id)
    return dict(row) if row else None


async def crear(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    nombre: str,
    descripcion: str | None,
    personas_incluidas: int,
    precio_base: Decimal,
    precio_persona_extra: Decimal,
    precio_hora: Decimal,
) -> dict[str, Any]:
    row = await conn.fetchrow(
        f"""
        INSERT INTO paquetes
            (sucursal_id, nombre, descripcion, personas_incluidas,
             precio_base, precio_persona_extra, precio_hora)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING {_RETURNING}
        """,
        sucursal_id,
        nombre,
        descripcion,
        personas_incluidas,
        precio_base,
        precio_persona_extra,
        precio_hora,
    )
    return dict(row)


async def actualizar(
    conn: asyncpg.Connection, paquete_id: UUID, updates: dict[str, Any]
) -> dict[str, Any] | None:
    if not updates:
        return await obtener(conn, paquete_id)
    set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
    set_parts.append("modificado = NOW()")
    sql = (
        f"UPDATE paquetes SET {', '.join(set_parts)} WHERE id = $1 AND activo = TRUE "
        f"RETURNING {_RETURNING}"
    )
    row = await conn.fetchrow(sql, paquete_id, *updates.values())
    return dict(row) if row else None


async def eliminar(conn: asyncpg.Connection, paquete_id: UUID) -> bool:
    result = await conn.execute(
        "UPDATE paquetes SET activo = FALSE, modificado = NOW() WHERE id = $1 AND activo = TRUE",
        paquete_id,
    )
    return bool(result == "UPDATE 1")


async def asociar_productos_a_paquete(
    conn: asyncpg.Connection,
    paquete_id: UUID,
    items: list[dict[str, Any]],
    usuario_id: UUID | None = None,
) -> None:
    """
    Inserta en lote las relaciones de alimentos/bebidas incluidos en el paquete.
    'items' es una lista de diccionarios con formato: [{"producto_id": UUID, "cantidad": int}]
    """
    if not items:
        return

    valores = []
    argumentos: list[Any] = [paquete_id, usuario_id]

    # $1=paquete_id, $2=usuario_id. Los pares producto/cantidad iteran desde $3
    for item in items:
        idx_prod = len(argumentos) + 1
        idx_cant = len(argumentos) + 2
        valores.append(f"(gen_random_uuid(), $1, ${idx_prod}, ${idx_cant}, TRUE, NOW(), $2)")
        argumentos.extend([item["producto_id"], item["cantidad"]])

    sql = f"""
        INSERT INTO public.paquete_productos
            (id, paquete_id, producto_id, cantidad, activo, creado, creado_por)
        VALUES {", ".join(valores)}
        ON CONFLICT (paquete_id, producto_id)
        DO UPDATE SET
            cantidad = EXCLUDED.cantidad,
            activo = TRUE,
            modificado = NOW(),
            modificado_por = $2;
    """
    await conn.execute(sql, *argumentos)


async def obtener_items_de_paquete(conn: asyncpg.Connection, paquete_id: UUID) -> list[dict[str, Any]]:
    """Retorna los productos incluidos en el paquete junto con su detalle base."""
    sql = """
        SELECT pp.producto_id, p.nombre, p.precio_unitario, p.tipo, pp.cantidad
        FROM public.paquete_productos pp
        INNER JOIN public.productos p ON pp.producto_id = p.id
        WHERE pp.paquete_id = $1 AND pp.activo = TRUE
        ORDER BY p.nombre ASC
    """
    rows = await conn.fetch(sql, paquete_id)
    return [dict(r) for r in rows]


async def desasociar_todos_los_productos_de_paquete(
    conn: asyncpg.Connection, paquete_id: UUID, usuario_id: UUID | None = None
) -> None:
    """Desactiva lógicamente todos los productos incluidos de un paquete. Útil antes de una
    actualización completa de la lista de incluidos."""
    await conn.execute(
        "UPDATE public.paquete_productos SET activo = FALSE, modificado = NOW(), modificado_por = $2 "
        "WHERE paquete_id = $1",
        paquete_id,
        usuario_id,
    )
