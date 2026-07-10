"""
app/repositories/combo_repository.py
Capa de datos para la gestión de productos dentro de un combo — SQL crudo con asyncpg.
Regla 11.1 y 11.4 SAD.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID
import asyncpg

_COLUMNS = "id, combo_id, producto_id, cantidad, activo, creado, creado_por"


async def asociar_productos_a_combo(
        conn: asyncpg.Connection,
        combo_id: UUID,
        items: list[dict[str, Any]],
        usuario_id: UUID | None = None
) -> None:
    """
    Inserta en lote (bulk insert) las relaciones del combo en producto_combo.
    'items' es una lista de diccionarios con formato: [{"producto_id": UUID, "cantidad": int}]
    """
    if not items:
        return

    # Construimos la consulta para una inserción eficiente
    valores = []
    argumentos = [combo_id, usuario_id]

    # El combo_id será $1 y creado_por será $2. Los elementos iteran desde $3 en adelante
    for i, item in enumerate(items):
        idx_prod = len(argumentos) + 1
        idx_cant = len(argumentos) + 2
        valores.append(f"(gen_random_uuid(), $1, ${idx_prod}, ${idx_cant}, TRUE, NOW(), $2)")
        argumentos.extend([item["producto_id"], item["cantidad"]])

    sql = f"""
        INSERT INTO public.producto_combo 
            (id, combo_id, producto_id, cantidad, activo, creado, creado_por)
        VALUES {', '.join(valores)}
        ON CONFLICT (combo_id, producto_id) 
        DO UPDATE SET cantidad = EXCLUDED.cantidad, activo = TRUE, modificado = NOW();
    """
    await conn.execute(sql, *argumentos)


async def obtener_items_de_combo(
        conn: asyncpg.Connection,
        combo_id: UUID
) -> list[dict[str, Any]]:
    """
    Retorna la lista de productos que integran el combo junto con su detalle base
    para poder pintarlo de manera óptima en el Front-end.
    """
    sql = """
          SELECT pc.producto_id, \
                 p.nombre, \
                 p.precio_unitario, \
                 p.tipo, \
                 pc.cantidad
          FROM public.producto_combo pc
                   INNER JOIN public.productos p ON pc.producto_id = p.id
          WHERE pc.combo_id = $1 \
            AND pc.activo = TRUE
          ORDER BY p.nombre ASC \
          """
    rows = await conn.fetch(sql, combo_id)
    return [dict(r) for r in rows]


async def desasociar_todos_los_productos(
        conn: asyncpg.Connection,
        combo_id: UUID
) -> None:
    """
    Desactiva o remueve lógicamente todos los productos de un combo.
    Útil antes de una actualización completa del combo.
    """
    await conn.execute(
        "UPDATE public.producto_combo SET activo = FALSE, modificado = NOW() WHERE combo_id = $1",
        combo_id
    )