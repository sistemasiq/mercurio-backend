"""
app/repositories/printer_repository.py
Capa de acceso a datos para config_impresora (por sucursal).
"""

from __future__ import annotations

import uuid
from typing import Any

import asyncpg

from app.core.utils import get_mexico_now


async def get_config_por_sucursal(conn: asyncpg.Connection, sucursal_id: str) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT id, sucursal_id, tipo, nombre_impresora, ancho_mm, alto_mm,
               driver_detectado, tipo_detectado, paper_names, override_manual,
               creado, modificado
        FROM public.config_impresora
        WHERE sucursal_id = $1
        ORDER BY tipo ASC
        """,
        uuid.UUID(sucursal_id),
    )
    return [dict(r) for r in rows]


async def get_config_por_tipo(
    conn: asyncpg.Connection, sucursal_id: str, tipo: str
) -> dict[str, Any] | None:
    row = await conn.fetchrow(
        """
        SELECT id, sucursal_id, tipo, nombre_impresora, ancho_mm, alto_mm,
               driver_detectado, tipo_detectado, paper_names, override_manual
        FROM public.config_impresora
        WHERE sucursal_id = $1 AND tipo = $2::tipo_impresora_tipo
        """,
        uuid.UUID(sucursal_id),
        tipo,
    )
    return dict(row) if row else None


async def upsert_config(
    conn: asyncpg.Connection,
    sucursal_id: str,
    tipo: str,
    nombre_impresora: str,
    ancho_mm: int | None = None,
    alto_mm: int | None = None,
    driver_detectado: str | None = None,
    tipo_detectado: str | None = None,
    paper_names: list[str] | None = None,
    override_manual: bool = False,
    modificado_por: str | None = None,
) -> dict[str, Any]:
    now = get_mexico_now()
    # ancho por defecto según tipo
    if ancho_mm is None:
        ancho_mm = 58 if tipo == "ticket" else 60
    if tipo_detectado is None:
        tipo_detectado = "desconocida"
    row = await conn.fetchrow(
        """
        INSERT INTO public.config_impresora
            (sucursal_id, tipo, nombre_impresora, ancho_mm, alto_mm, driver_detectado, tipo_detectado, paper_names, override_manual, creado_por, creado, modificado, modificado_por)
        VALUES ($1, $2::tipo_impresora_tipo, $3, $4, $5, $6, $7::tipo_impresora_detectado, $8, $9, $10, $11, $11, $10)
        ON CONFLICT (sucursal_id, tipo) DO UPDATE SET
            nombre_impresora = EXCLUDED.nombre_impresora,
            ancho_mm = EXCLUDED.ancho_mm,
            alto_mm = EXCLUDED.alto_mm,
            driver_detectado = EXCLUDED.driver_detectado,
            tipo_detectado = EXCLUDED.tipo_detectado,
            paper_names = EXCLUDED.paper_names,
            override_manual = EXCLUDED.override_manual,
            modificado = EXCLUDED.modificado,
            modificado_por = EXCLUDED.modificado_por
        RETURNING id, sucursal_id, tipo, nombre_impresora, ancho_mm, alto_mm, driver_detectado, tipo_detectado, paper_names, override_manual
        """,
        uuid.UUID(sucursal_id),
        tipo,
        nombre_impresora,
        ancho_mm,
        alto_mm,
        driver_detectado,
        tipo_detectado,
        paper_names or [],
        override_manual,
        uuid.UUID(modificado_por) if modificado_por else None,
        now,
    )
    assert row is not None
    return dict(row)


async def delete_config(conn: asyncpg.Connection, sucursal_id: str, tipo: str) -> bool:
    result = await conn.execute(
        """
        DELETE FROM public.config_impresora
        WHERE sucursal_id = $1 AND tipo = $2::tipo_impresora_tipo
        """,
        uuid.UUID(sucursal_id),
        tipo,
    )
    return result != "DELETE 0"
