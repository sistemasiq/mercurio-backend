from typing import Any
from uuid import UUID

import asyncpg

TIME_FOR_CHECK_RESERVATIONS = '15 minutes'

_COLUMNS = """
   id, sucursal_id, tipo_evento_id, paquete_id,
   nombre_cliente, apellidos_cliente, telefono_cliente, email_cliente, notas_cliente,
   nombre_festejado, edad_festejado,
   fecha_evento, hora_inicio, hora_fin,
   numero_personas, precio_base, precio_personas_extra, precio_extras,
   descuento, precio_total, anticipo, saldo_pendiente,
   estado, notas, activo, creado, creado_por, modificado, modificado_por
"""

_COLUMNAS_NECESARIAS_PARA_ESTANCIA = """
   id,nombre_cliente,apellidos_cliente,telefono_cliente,hora_inicio,
   hora_fin,numero_personas,fecha_evento
"""

_SELECT = f"SELECT {_COLUMNS} FROM reservaciones"

_SELECT_ESTANCIA = (
   f"SELECT {_COLUMNAS_NECESARIAS_PARA_ESTANCIA} "
   "FROM reservaciones "
   "WHERE fecha_evento = CURRENT_DATE "
   "AND hora_inicio < ((CURRENT_TIME AT TIME ZONE 'UTC' AT TIME ZONE 'America/Mexico_City')::time "
   f"+ INTERVAL '{TIME_FOR_CHECK_RESERVATIONS}') "
   "AND hora_fin > (CURRENT_TIME AT TIME ZONE 'UTC' AT TIME ZONE 'America/Mexico_City')::time "
   "AND saldo_pendiente = 0 "
   "AND activo = TRUE"
)


async def listar(conn: asyncpg.Connection, sucursal_id: str | None = None) -> list[dict[str, Any]]:
    if sucursal_id is not None:
        rows = await conn.fetch(
            _SELECT + " WHERE activo = TRUE AND sucursal_id = $1 ORDER BY fecha_evento",
            sucursal_id,
        )
    else:
        rows = await conn.fetch(_SELECT + " WHERE activo = TRUE ORDER BY fecha_evento")
    return [dict(r) for r in rows]


async def obtener(conn: asyncpg.Connection, reservacion_id: UUID) -> dict[str, Any] | None:
   row = await conn.fetchrow(_SELECT + " WHERE id = $1", reservacion_id)
   return dict(row) if row else None

async def obtener_evento_mas_cercano(conn: asyncpg.Connection, sucursal_id: UUID) -> dict[str, Any] | None:
   row = await conn.fetchrow(_SELECT_ESTANCIA+ " AND sucursal_id = $1", sucursal_id)
   return dict(row) if row else None

async def crear(conn: asyncpg.Connection, data: dict[str, Any]) -> dict[str, Any]:
   cols = ", ".join(data.keys())
   placeholders = ", ".join(f"${i + 1}" for i in range(len(data)))
   sql = f"INSERT INTO reservaciones ({cols}) VALUES ({placeholders}) " f"RETURNING {_COLUMNS}"
   row = await conn.fetchrow(sql, *data.values())
   return dict(row)


async def actualizar(
   conn: asyncpg.Connection, reservacion_id: UUID, updates: dict[str, Any]
) -> dict[str, Any] | None:
   if not updates:
       return await obtener(conn, reservacion_id)
   set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
   set_parts.append("modificado = NOW()")
   sql = (
       f"UPDATE reservaciones SET {', '.join(set_parts)} WHERE id = $1 AND activo = TRUE "
       f"RETURNING {_COLUMNS}"
   )
   row = await conn.fetchrow(sql, reservacion_id, *updates.values())
   return dict(row) if row else None


async def eliminar(conn: asyncpg.Connection, reservacion_id: UUID) -> bool:
   result = await conn.execute(
       "UPDATE reservaciones SET activo = FALSE, modificado = NOW() "
       "WHERE id = $1 AND activo = TRUE",
       reservacion_id,
   )
   return bool(result == "UPDATE 1")
