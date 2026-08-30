"""
app/repositories/comanda_repository.py
Única capa que habla con la BD — SQL crudo con asyncpg.
Regla 11.1 y 11.4 SAD: solo SQL parametrizado aquí, nada de lógica de negocio.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

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
        nombre=row.get("nombre"),
        producto_nombre=row.get("nombre"),  # alias del JOIN
        nombre_combo_padre=row.get("nombre_combo_padre"),
        es_hijo_de=str(row["es_hijo_de"]) if row.get("es_hijo_de") else None,
        es_hijo_combo=bool(row.get("es_hijo_combo", False)),
        id_combo_padre=str(row["id_combo_padre"]) if row.get("id_combo_padre") else None,
    )


def _row_to_comanda(
    row: asyncpg.Record, detalles: list[DetalleComanda | dict[str, Any]]
) -> Comanda:
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


def _campos_insercion_detalle(item: Any) -> tuple[Any, ...]:
    if isinstance(item, dict):
        producto_id = str(item.get("producto_id") or item["id"])
        cantidad = item["cantidad"]
        precio_unitario = Decimal(str(item["precio_unitario"]))
        importe = Decimal(str(item.get("subtotal", item.get("importe", 0))))
        notas = item.get("notas_especiales")
        nombre_combo_padre = item.get("nombre_combo_padre")
        es_hijo_de = str(item["es_hijo_de"]) if item.get("es_hijo_de") else None
        es_hijo_combo = bool(item.get("es_hijo_combo", False))
        id_combo_padre = item.get("id_combo_padre")
        return (
            producto_id,
            cantidad,
            precio_unitario,
            importe,
            notas,
            nombre_combo_padre,
            es_hijo_de,
            es_hijo_combo,
            id_combo_padre,
        )

    return (
        str(item.id),
        item.cantidad,
        item.precio_unitario,
        item.subtotal,
        item.notas_especiales,
        getattr(item, "nombre_combo_padre", None),
        str(item.es_hijo_de) if getattr(item, "es_hijo_de", None) else None,
        bool(getattr(item, "es_hijo_combo", False)),
        getattr(item, "id_combo_padre", None),
    )


async def crear_comanda_con_detalles(
    conn: asyncpg.Connection,
    comanda_in: ComandaCreate,
    detalles_procesados: list[Any] | None = None,
    creado_por: str | None = None,
) -> Comanda:
    """
    Inserta comanda + detalles en una transacción.
    Regla 11.4: SQL solo en el repositorio.
    """
    if not creado_por:
        raise ValueError("crear_comanda_con_detalles requiere creado_por no nulo.")
    comanda_id = str(uuid.uuid4())
    fecha = get_mexico_now()

    async with conn.transaction():
        await conn.execute(
            """
            INSERT INTO public.comandas
                (id, ticket_numero, estado_actual, total_final,
                 sucursal_id, fecha_hora, creado_por, nombre_cliente)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            comanda_id,
            comanda_in.ticket_numero,
            comanda_in.estado_actual.value,
            comanda_in.total_final,
            comanda_in.sucursal_id,
            fecha,
            creado_por,
            comanda_in.nombre_cliente,
        )

        detalles = (
            detalles_procesados if detalles_procesados is not None else comanda_in.detalles_comanda
        )

        for item in detalles:
            (
                producto_id,
                cantidad,
                precio_unitario,
                importe,
                notas,
                nombre_combo_padre,
                es_hijo_de,
                es_hijo_combo,
                id_combo_padre,
            ) = _campos_insercion_detalle(item)
            await conn.execute(
                """
                INSERT INTO public.detalles_comanda
                    (id, comanda_id, producto_id, cantidad, precio_unitario, importe,
                    sucursal_id, notas_especiales, nombre_combo_padre, es_hijo_de,
                    es_hijo_combo, id_combo_padre, creado_por)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                str(uuid.uuid4()),
                comanda_id,
                producto_id,
                cantidad,
                precio_unitario,
                importe,
                comanda_in.sucursal_id,
                notas,
                nombre_combo_padre,
                es_hijo_de,
                es_hijo_combo,
                id_combo_padre,
                creado_por,
            )

    # Releer para devolver el objeto completo
    comanda = await get_comanda_por_id(conn, comanda_id)
    assert comanda is not None, "la comanda recién insertada debe existir"
    return comanda


async def actualizar_estado_comanda(
    conn: asyncpg.Connection,
    comanda_id: str,
    nuevo_estado: str,
    usuario_id: str | None = None,
    *,
    motivo_cancelacion: str | None = None,
    desactivar: bool = False,
) -> Comanda | None:
    """Actualiza el estado de una comanda con auditoría.

    Parámetros opcionales (solo para cancelaciones):
      - motivo_cancelacion: obligatorio cuando nuevo_estado == 'C'.
      - desactivar: si True, pone activo = FALSE (cancelación).

    Retorna None si no existe la comanda.
    """
    sin_motivo = not motivo_cancelacion or not motivo_cancelacion.strip()
    if nuevo_estado == "C" and desactivar and sin_motivo:
        raise ValueError("El motivo de cancelación es obligatorio al cancelar una comanda.")

    result = await conn.execute(
        """
        UPDATE public.comandas
        SET estado_actual = $1,
            activo = CASE WHEN $4 THEN FALSE ELSE activo END,
            motivo_cancelacion = CASE WHEN $4 THEN $5 ELSE motivo_cancelacion END,
            modificado = now(),
            modificado_por = $2
        WHERE id = $3
        """,
        nuevo_estado,
        uuid.UUID(usuario_id) if usuario_id else None,
        uuid.UUID(comanda_id),
        desactivar,
        motivo_cancelacion.strip() if desactivar and motivo_cancelacion else None,
    )
    # asyncpg retorna 'UPDATE N' — si N=0, la comanda no existía
    if result == "UPDATE 0":
        return None
    return await get_comanda_por_id(conn, comanda_id)


async def modificar_comanda_parcial(
    conn: asyncpg.Connection,
    comanda_id: str,
    detalles_a_eliminar: list[str],
    usuario_id: str | None = None,
    motivo_cancelacion: str | None = None,
) -> Comanda | None:
    """Elimina productos específicos de una comanda en estado 'P'.

    Si tras eliminar los productos seleccionados no quedan detalles activos,
    cancela automáticamente la comanda (estado 'C', activo=False) en vez de
    dejarla vacía.  En ese caso *requiere* motivo_cancelacion.

    Para la cancelación total, los detalles restantes se desactivan
    (activo=False) en vez de borrarse físicamente, preservando el historial.

    Retorna None si la comanda no existe o no está en estado 'P'.
    """
    comanda = await get_comanda_por_id(conn, comanda_id)
    if comanda is None or comanda.estado_actual != "P":
        return None

    uid = uuid.UUID(usuario_id) if usuario_id else None

    async with conn.transaction():
        # 1) Eliminar físicamente los detalles seleccionados
        ids_validos: list[uuid.UUID] = []
        for detalle_id in detalles_a_eliminar:
            try:
                parsed_id = uuid.UUID(detalle_id)
            except (ValueError, AttributeError):
                continue
            ids_validos.append(parsed_id)

        for parsed_id in ids_validos:
            await conn.execute(
                "DELETE FROM public.detalles_comanda WHERE id = $1 AND comanda_id = $2",
                parsed_id,
                uuid.UUID(comanda_id),
            )

        # 2) Contar detalles activos restantes
        restantes = await conn.fetchval(
            "SELECT COUNT(*)::int FROM public.detalles_comanda "
            "WHERE comanda_id = $1 AND activo = TRUE",
            uuid.UUID(comanda_id),
        )

        if restantes == 0:
            # ── Autocancelación ──────────────────────────────────────
            if not motivo_cancelacion or not motivo_cancelacion.strip():
                raise ValueError(
                    "El motivo de cancelación es obligatorio cuando se "
                    "eliminan todos los productos de la comanda."
                )

            # Desactivar todos los detalles restantes (soft-delete)
            await conn.execute(
                """
                UPDATE public.detalles_comanda
                SET activo = FALSE,
                    modificado = now(),
                    modificado_por = $2
                WHERE comanda_id = $1
                """,
                uuid.UUID(comanda_id),
                uid,
            )

            # Cancelar la comanda (preservar total_final original)
            await conn.execute(
                """
                UPDATE public.comandas
                SET estado_actual = 'C',
                    activo = FALSE,
                    motivo_cancelacion = $1,
                    modificado = now(),
                    modificado_por = $2
                WHERE id = $3
                """,
                motivo_cancelacion.strip(),
                uid,
                uuid.UUID(comanda_id),
            )
        else:
            # ── Eliminación parcial (comportamiento original) ─────────
            nuevo_total = await conn.fetchval(
                """
                SELECT COALESCE(SUM(importe), 0)
                FROM public.detalles_comanda
                WHERE comanda_id = $1
                """,
                uuid.UUID(comanda_id),
            )

            await conn.execute(
                """
                UPDATE public.comandas
                SET total_final = $1,
                    modificado = now(),
                    modificado_por = $2
                WHERE id = $3
                """,
                nuevo_total,
                uid,
                uuid.UUID(comanda_id),
            )

    return await get_comanda_por_id(conn, comanda_id)


async def eliminar_detalle_comanda(
    conn: asyncpg.Connection,
    comanda_id: str,
    detalle_id: str,
) -> bool:
    """Elimina un detalle específico de una comanda en estado 'P'.

    Retorna True si se eliminó correctamente, False si la comanda no existe,
    no está en pendiente o el detalle no pertenece a la comanda.
    """
    comanda = await get_comanda_por_id(conn, comanda_id)
    if comanda is None or comanda.estado_actual != "P":
        return False

    result = await conn.execute(
        """
        DELETE FROM public.detalles_comanda
        WHERE id = $1 AND comanda_id = $2
        """,
        uuid.UUID(detalle_id),
        uuid.UUID(comanda_id),
    )
    return bool(result != "DELETE 0")


async def get_comandas_pendientes(
    conn: asyncpg.Connection, sucursal_id: str | None = None
) -> list[Comanda]:
    # 1. Fuerza el casteo en SQL: $1::uuid
    filtro_sucursal = "AND c.sucursal_id = $1::uuid" if sucursal_id is not None else ""

    # 2. Asegura que el parámetro sea string (asyncpg maneja UUID desde string)
    params = [str(sucursal_id)] if sucursal_id is not None else []

    rows = await conn.fetch(
        f"""
        SELECT
            c.id, c.ticket_numero, c.estado_actual, c.total_final,
            c.sucursal_id, c.fecha_hora, c.nombre_cliente,
            dc.id AS detalle_id,
            dc.producto_id,
            dc.cantidad,
            dc.precio_unitario,
            dc.importe,
            dc.notas_especiales,
            dc.nombre_combo_padre,
            dc.es_hijo_de,
            dc.es_hijo_combo,
            dc.id_combo_padre,
            p.nombre,
            p.tipo AS producto_tipo
        FROM public.comandas c
        LEFT JOIN public.detalles_comanda dc ON dc.comanda_id = c.id
        LEFT JOIN public.productos p ON p.id = dc.producto_id
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
                nombre_cliente=row.get("nombre_cliente"),
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
                    nombre=row.get("nombre"),
                    producto_nombre=row.get("nombre"),
                    producto_tipo=row.get("producto_tipo"),
                    nombre_combo_padre=row.get("nombre_combo_padre"),
                    es_hijo_de=str(row["es_hijo_de"]) if row.get("es_hijo_de") else None,
                    es_hijo_combo=bool(row.get("es_hijo_combo", False)),
                    id_combo_padre=(
                        str(row["id_combo_padre"]) if row.get("id_combo_padre") else None
                    ),
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
            c.sucursal_id, c.fecha_hora, c.nombre_cliente,
            dc.id              AS detalle_id,
            dc.producto_id,
            dc.cantidad,
            dc.precio_unitario,
            dc.importe,
            dc.notas_especiales,
            dc.nombre_combo_padre,
            dc.es_hijo_de,
            dc.es_hijo_combo,
            dc.id_combo_padre,
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
        nombre_cliente=rows[0].get("nombre_cliente"),
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
                    nombre=row.get("nombre"),
                    producto_nombre=row.get("nombre"),
                    producto_tipo=row.get("producto_tipo"),
                    nombre_combo_padre=row.get("nombre_combo_padre"),
                    es_hijo_de=str(row["es_hijo_de"]) if row.get("es_hijo_de") else None,
                    es_hijo_combo=bool(row.get("es_hijo_combo", False)),
                    id_combo_padre=(
                        str(row["id_combo_padre"]) if row.get("id_combo_padre") else None
                    ),
                )
            )

    return comanda
