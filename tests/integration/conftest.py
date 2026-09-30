"""Fixtures de integración: se conectan a la BD compartida real de desarrollo
(DATABASE_URL en .env). No hay BD de pruebas aislada en este proyecto -- cada
fixture que inserte datos debe limpiarlos ella misma."""
import os
import uuid

import asyncpg
import pytest_asyncio
from dotenv import load_dotenv

load_dotenv()


@pytest_asyncio.fixture
async def conn():
    connection = await asyncpg.connect(os.environ["DATABASE_URL"])
    yield connection
    await connection.close()


# Datos reales ya usados durante la sesión de QA de Cierre de Caja
# (cajero Oscar Magana Jaime / CAJA 01 / La Piedad Centro / Turno Matutino).
CAJA_ID = "c72017a5-7e06-4b7a-8c63-65c9f6e9047d"
CAJERO_ID = "0c81cb1e-8627-469b-abc2-f4198526e2a8"
TURNO_ID = "d943ab94-4e94-4fcd-b15a-4601cc1c8427"
EFECTIVO_ID = "c400c82d-8fb1-4f10-9180-21c5bdeb92ea"
TARJETA_ID = "b827363b-6453-40e4-9536-f7a004711f91"  # metodos_pago.tipo = 'T' (catálogo global, migración 037)


@pytest_asyncio.fixture
async def apertura_prueba(conn):
    """Crea una apertura_caja desechable (fondo_inicial=1000.00) para pruebas
    de integración y la limpia (movimientos_caja + apertura_caja) al terminar,
    incluso si el test falla a medias. Si el cajero o la caja de prueba ya
    tenían una apertura activa (violaría los índices únicos parciales
    uq_apertura_cajero_activo / uq_apertura_caja_activa), se cierran
    temporalmente y se restauran a su estado original al terminar -- nunca se
    pierden ni quedan cerradas para siempre."""
    previas = await conn.fetch(
        """
        SELECT id, estado FROM public.apertura_caja
        WHERE (cajero_id = $1 OR caja_id = $2) AND estado IN ('ABIERTA', 'EN_CORTE')
        """,
        uuid.UUID(CAJERO_ID), uuid.UUID(CAJA_ID),
    )
    for prev in previas:
        await conn.execute(
            "UPDATE public.apertura_caja SET estado = 'CERRADA' WHERE id = $1", prev["id"]
        )
    row = await conn.fetchrow(
        """
        INSERT INTO public.apertura_caja (caja_id, cajero_id, turno_id, fondo_inicial, estado)
        VALUES ($1, $2, $3, 1000.00, 'ABIERTA')
        RETURNING id
        """,
        uuid.UUID(CAJA_ID), uuid.UUID(CAJERO_ID), uuid.UUID(TURNO_ID),
    )
    apertura_id = str(row["id"])
    try:
        yield apertura_id
    finally:
        await conn.execute(
            "DELETE FROM public.retiros_parciales WHERE apertura_caja_id = $1", uuid.UUID(apertura_id)
        )
        await conn.execute(
            "DELETE FROM public.movimientos_caja WHERE apertura_caja_id = $1", uuid.UUID(apertura_id)
        )
        await conn.execute(
            "DELETE FROM public.apertura_caja WHERE id = $1", uuid.UUID(apertura_id)
        )
        for prev in previas:
            await conn.execute(
                "UPDATE public.apertura_caja SET estado = $2 WHERE id = $1",
                prev["id"], prev["estado"],
            )
