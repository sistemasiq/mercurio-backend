"""
app/repositories/folio_repository.py
Folio de ticket secuencial por sucursal (QA #21). `siguiente_folio` hace un
UPDATE ... RETURNING atómico (si dos cobros llegan a la vez para la misma
sucursal, Postgres serializa las dos filas y cada una obtiene un número
distinto sin necesidad de un lock explícito).
"""

from __future__ import annotations

from uuid import UUID

import asyncpg

_UPSERT_Y_RETURN = """
    INSERT INTO public.folios_sucursal (sucursal_id, serie, ultimo)
    VALUES ($1, 'A', 1)
    ON CONFLICT (sucursal_id) DO UPDATE
        SET ultimo = public.folios_sucursal.ultimo + 1
    RETURNING serie, ultimo
"""


async def siguiente_folio(conn: asyncpg.Connection, sucursal_id: UUID) -> str:
    """Asigna y devuelve el siguiente folio de ticket para la sucursal, con
    formato "<serie>-<ultimo>" recortado a 10 caracteres
    (comandas.ticket_numero es VARCHAR(10))."""
    row = await conn.fetchrow(_UPSERT_Y_RETURN, sucursal_id)
    serie = row["serie"]
    ultimo = row["ultimo"]
    folio = f"{serie}{ultimo}"
    return folio[:10]
