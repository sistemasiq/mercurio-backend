"""
app/repositories/comanda_repository.py
Única capa que habla con la BD — SQL crudo con asyncpg.
Regla 11.1 y 11.4 SAD: solo SQL parametrizado aquí, nada de lógica de negocio.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

import asyncpg

from app.core.utils import get_mexico_now
from app.models.comanda import Comanda, DetalleComanda

if TYPE_CHECKING:
    from app.schemas.comanda import ComandaCreate

# ── Helpers de conversión ─────────────────────────────────────────────────────


def _row_to_detalle(row: asyncpg.Record) -> DetalleComanda:
    return DetalleComanda(
        id=str(row["id"]),
        comanda_id=str(row["comanda_id"]),
        producto_id=str(row["producto_id"]),
        cantidad=row["cantidad"],
        precio_unitario=Decimal(str(row["precio_unitario"])),
        importe=Decimal(str(row["importe"])),
        sucursal_id=str(row["sucursal_id"]),
        notas_especiales=row.get("notas_especiales"),
        producto_nombre=row.get("nombre"),  # alias del JOIN
    )


def _row_to_comanda(row: asyncpg.Record, detalles: list[DetalleComanda]) -> Comanda:
    return Comanda(
        id=str(row["id"]),
        ticket_numero=row["ticket_numero"],
        estado_actual=row["estado_actual"],
        total_final=Decimal(str(row["total_final"])),
        sucursal_id=str(row["sucursal_id"]),
        fecha_hora=row.get("fecha_hora"),
        detalles=detalles,
    )


# ── Queries ───────────────────────────────────────────────────────────────────


async def crear_comanda_con_detalles(
    conn: asyncpg.Connection,
    comanda_in: ComandaCreate,
) -> Comanda:
    """
    Inserta comanda + detalles en una transacción.
    Regla 11.4: SQL solo en el repositorio.
    """
    comanda_id = str(uuid.uuid4())
    fecha = get_mexico_now()

    async with conn.transaction():
        await conn.execute(
            """
            INSERT INTO public.comandas
                (id, ticket_numero, estado_actual, total_final, sucursal_id, fecha_hora)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            comanda_id,
            comanda_in.ticket_numero,
            comanda_in.estado_actual.value,
            comanda_in.total_final,
            comanda_in.sucursal_id,
            fecha,
        )

        for item in comanda_in.detalles_comanda:
            await conn.execute(
                """
                INSERT INTO public.detalles_comanda
                    (id, comanda_id, producto_id, cantidad, precio_unitario, importe,
                     sucursal_id, notas_especiales)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                str(uuid.uuid4()),
                comanda_id,
                item.id,
                item.cantidad,
                item.precio_unitario,
                item.subtotal,
                comanda_in.sucursal_id,
                item.notas_especiales,
            )

    # Releer para devolver el objeto completo
    comanda = await get_comanda_por_id(conn, comanda_id)
    assert comanda is not None, "la comanda recién insertada debe existir"
    return comanda


async def actualizar_estado_comanda(
    conn: asyncpg.Connection,
    comanda_id: str,
    nuevo_estado: str,
) -> Comanda | None:
    """Actualiza el estado de una comanda. Retorna None si no existe."""
    result = await conn.execute(
        """
        UPDATE public.comandas
        SET estado_actual = $1
        WHERE id = $2
        """,
        nuevo_estado,
        comanda_id,
    )
    # asyncpg retorna 'UPDATE N' — si N=0, la comanda no existía
    if result == "UPDATE 0":
        return None
    return await get_comanda_por_id(conn, comanda_id)


async def get_comandas_pendientes(
    conn: asyncpg.Connection, sucursal_id: str | None = None
) -> list[Comanda]:
    """Retorna comandas en estado P, E o L con sus detalles.

    Si sucursal_id es None no filtra por sucursal (uso exclusivo de
    AdministradorSistema, que ve todas las sucursales)."""
    filtro_sucursal = "AND c.sucursal_id = $1" if sucursal_id is not None else ""
    params: list[str] = [sucursal_id] if sucursal_id is not None else []
    rows = await conn.fetch(
        f"""
        SELECT
            c.id, c.ticket_numero, c.estado_actual, c.total_final,
            c.sucursal_id, c.fecha_hora,
            dc.id              AS detalle_id,
            dc.producto_id,
            dc.cantidad,
            dc.precio_unitario,
            dc.importe,
            dc.notas_especiales,
            p.nombre,
            p.tipo AS producto_tipo
        FROM public.comandas c
        LEFT JOIN public.detalles_comanda dc ON dc.comanda_id = c.id
        LEFT JOIN public.productos        p  ON p.id = dc.producto_id
        WHERE c.estado_actual IN ('P', 'E', 'L')
        {filtro_sucursal}
        ORDER BY c.fecha_hora ASC
        """,
        *params,
    )

    # Agrupar detalles por comanda
    comandas_map: dict[str, Comanda] = {}
    for row in rows:
        cid = str(row["id"])
        if cid not in comandas_map:
            comandas_map[cid] = Comanda(
                id=cid,
                ticket_numero=row["ticket_numero"],
                estado_actual=row["estado_actual"],
                total_final=Decimal(str(row["total_final"])),
                sucursal_id=str(row["sucursal_id"]),
                fecha_hora=row.get("fecha_hora"),
                detalles=[],
            )
        if row["detalle_id"] is not None:
            comandas_map[cid].detalles.append(
                DetalleComanda(
                    id=str(row["detalle_id"]),
                    comanda_id=cid,
                    producto_id=str(row["producto_id"]),
                    cantidad=row["cantidad"],
                    precio_unitario=Decimal(str(row["precio_unitario"])),
                    importe=Decimal(str(row["importe"])),
                    sucursal_id=str(row["sucursal_id"]),
                    notas_especiales=row.get("notas_especiales"),
                    producto_nombre=row.get("nombre"),
                    producto_tipo=row.get("producto_tipo"),
                )
            )

    return list(comandas_map.values())


async def get_comanda_por_id(
    conn: asyncpg.Connection,
    comanda_id: str,
) -> Comanda | None:
    """Obtiene una comanda con sus detalles por ID."""
    rows = await conn.fetch(
        """
        SELECT
            c.id, c.ticket_numero, c.estado_actual, c.total_final,
            c.sucursal_id, c.fecha_hora,
            dc.id              AS detalle_id,
            dc.producto_id,
            dc.cantidad,
            dc.precio_unitario,
            dc.importe,
            dc.notas_especiales,
            p.nombre,
            p.tipo AS producto_tipo
        FROM public.comandas c
        LEFT JOIN public.detalles_comanda dc ON dc.comanda_id = c.id
        LEFT JOIN public.productos        p  ON p.id = dc.producto_id
        WHERE c.id = $1
        """,
        comanda_id,
    )

    if not rows:
        return None

    comanda = Comanda(
        id=str(rows[0]["id"]),
        ticket_numero=rows[0]["ticket_numero"],
        estado_actual=rows[0]["estado_actual"],
        total_final=Decimal(str(rows[0]["total_final"])),
        sucursal_id=str(rows[0]["sucursal_id"]),
        fecha_hora=rows[0].get("fecha_hora"),
        detalles=[],
    )

    for row in rows:
        if row["detalle_id"] is not None:
            comanda.detalles.append(
                DetalleComanda(
                    id=str(row["detalle_id"]),
                    comanda_id=str(row["id"]),
                    producto_id=str(row["producto_id"]),
                    cantidad=row["cantidad"],
                    precio_unitario=Decimal(str(row["precio_unitario"])),
                    importe=Decimal(str(row["importe"])),
                    sucursal_id=str(row["sucursal_id"]),
                    notas_especiales=row.get("notas_especiales"),
                    producto_nombre=row.get("nombre"),
                    producto_tipo=row.get("producto_tipo"),
                )
            )

    return comanda
