from typing import Any
from uuid import UUID

import asyncpg

_SELECT_CON_SUCURSAL = """
    SELECT mp.id, mp.nombre, mp.descripcion, mp.tipo, mp.creado, mp.creado_por,
           mp.modificado, mp.modificado_por,
           COALESCE(smp.activo, TRUE) AS activo
    FROM metodos_pago mp
    LEFT JOIN sucursal_metodos_pago smp
        ON smp.metodo_pago_id = mp.id AND smp.sucursal_id = $1
"""

# AdministradorSistema no tiene una sucursal propia contra la cual resolver
# `activo`; se le muestra el catálogo con activo=TRUE de forma neutral, ya
# que gestiona nombre/descripción, no activación (eso es por sucursal).
_SELECT_SIN_SUCURSAL = """
    SELECT mp.id, mp.nombre, mp.descripcion, mp.tipo, mp.creado, mp.creado_por,
           mp.modificado, mp.modificado_por, TRUE AS activo
    FROM metodos_pago mp
"""


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[dict[str, Any]]:
    if sucursal_id is not None:
        rows = await conn.fetch(_SELECT_CON_SUCURSAL + " ORDER BY mp.tipo", sucursal_id)
    else:
        rows = await conn.fetch(_SELECT_SIN_SUCURSAL + " ORDER BY mp.tipo")
    return [dict(r) for r in rows]


async def obtener(
    conn: asyncpg.Connection, metodo_pago_id: UUID, sucursal_id: UUID | None = None
) -> dict[str, Any] | None:
    if sucursal_id is not None:
        row = await conn.fetchrow(
            _SELECT_CON_SUCURSAL + " WHERE mp.id = $2", sucursal_id, metodo_pago_id
        )
    else:
        row = await conn.fetchrow(_SELECT_SIN_SUCURSAL + " WHERE mp.id = $1", metodo_pago_id)
    return dict(row) if row else None


async def existe(conn: asyncpg.Connection, metodo_pago_id: UUID) -> bool:
    row = await conn.fetchrow("SELECT 1 FROM metodos_pago WHERE id = $1", metodo_pago_id)
    return row is not None


async def obtener_ids_por_tipo(conn: asyncpg.Connection, tipo: str) -> set[UUID]:
    """Resuelve los ids de metodos_pago cuyo `tipo` coincide. Desde la
    migración 037 hay como máximo una fila por tipo (UNIQUE (tipo)), pero se
    devuelve un set para no asumir esa invariante en el llamador."""
    rows = await conn.fetch("SELECT id FROM metodos_pago WHERE tipo = $1", tipo)
    return {r["id"] for r in rows}


async def actualizar_catalogo(
    conn: asyncpg.Connection, metodo_pago_id: UUID, updates: dict[str, Any]
) -> None:
    """Edita nombre/descripción del catálogo global. El `tipo` no es
    editable: es la identidad fija de cada una de las 5 filas."""
    set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
    set_parts.append("modificado = NOW()")
    sql = f"UPDATE metodos_pago SET {', '.join(set_parts)} WHERE id = $1"
    await conn.execute(sql, metodo_pago_id, *updates.values())


async def set_activacion(
    conn: asyncpg.Connection,
    metodo_pago_id: UUID,
    sucursal_id: UUID,
    activo: bool,
    modificado_por: UUID | None,
) -> None:
    await conn.execute(
        """
        INSERT INTO sucursal_metodos_pago (sucursal_id, metodo_pago_id, activo, modificado_por)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (sucursal_id, metodo_pago_id)
        DO UPDATE SET
            activo = EXCLUDED.activo,
            modificado = NOW(),
            modificado_por = EXCLUDED.modificado_por
        """,
        sucursal_id,
        metodo_pago_id,
        activo,
        modificado_por,
    )
