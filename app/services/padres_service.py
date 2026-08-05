from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

import asyncpg

from app.core.security import create_access_token
from app.repositories.branch_repository import get_sucursal_by_id
from app.repositories.tutores import get_tutor_by_id
from app.schemas.padres import (
    NinoActivoResponse,
    PadreDashboardResponse,
    SucursalInfo,
    TutorInfo,
)


class TokenAccesoInvalido(Exception):
    pass


async def _get_hijos_visita(
    conn: asyncpg.Connection, registro_id: UUID
) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT
            n.id,
            n.nombre_completo AS "nombreCompleto",
            n.edad,
            CASE
                WHEN dr.salida IS NULL THEN 'activo'
                ELSE 'terminado'
            END AS "estadoVisita",
            dr.entrada AT TIME ZONE 'America/Mexico_City' AS "horaEntrada",
            dr.salida_esperada AT TIME ZONE 'America/Mexico_City' AS "horaSalidaEsperada",
            dr.salida AT TIME ZONE 'America/Mexico_City' AS "horaSalida",
            CASE
                WHEN dr.salida IS NULL
                THEN FLOOR(EXTRACT(EPOCH FROM (NOW() AT TIME ZONE 'America/Mexico_City' - dr.entrada)) / 60)::int
                ELSE FLOOR(EXTRACT(EPOCH FROM (dr.salida - dr.entrada)) / 60)::int
            END AS "minutosTranscurridos",
            (dr.cantidad * 60)::int AS "minutosPagados",
            p.pulsera_rfid AS "pulsera"
        FROM detalles_registro dr
        JOIN registros r ON r.id = dr.registros_id
        JOIN ninos n ON n.id = dr.ninos_id
        JOIN pulseras p ON p.id = dr.pulseras_id
        WHERE r.id = $1
          AND r.estado = 'A'
          AND dr.activo = TRUE
        ORDER BY
            CASE WHEN dr.salida IS NULL THEN 0 ELSE 1 END,
            dr.entrada DESC
        """,
        registro_id,
    )
    return [dict(r) for r in rows]


async def get_padre_dashboard(
    conn: asyncpg.Connection, raw_code: str
) -> PadreDashboardResponse:
    try:
        registro_id = UUID(raw_code)
    except ValueError:
        raise TokenAccesoInvalido

    registro = await conn.fetchrow(
        """
        SELECT r.tutores_id AS "tutorId",
               r.sucursal_id AS "sucursalId"
        FROM registros r
        WHERE r.id = $1
          AND r.activo = TRUE
          AND r.estado = 'A'
        """,
        registro_id,
    )
    if registro is None:
        raise TokenAccesoInvalido

    tutor = await get_tutor_by_id(conn, registro["tutorId"])
    if tutor is None:
        raise TokenAccesoInvalido

    sucursal = await get_sucursal_by_id(conn, registro["sucursalId"])
    if sucursal is None:
        raise TokenAccesoInvalido

    hijos = await _get_hijos_visita(conn, registro_id)

    expires_delta = timedelta(hours=2)
    access_token = create_access_token(
        payload={
            "sub": str(registro_id),
            "tutor_id": str(tutor["id"]),
            "sucursal_id": str(sucursal["id"]),
            "role": "PadreVisor",
        },
        expires_delta=expires_delta,
    )

    return PadreDashboardResponse(
        token=access_token,
        expires_in=int(expires_delta.total_seconds()),
        tutor=TutorInfo(
            id=tutor["id"],
            nombreCompleto=tutor["nombreCompleto"],
            telefono=tutor["telefono"],
            sucursal=SucursalInfo(
                id=sucursal["id"],
                nombre=sucursal["nombre"],
            ),
        ),
        ninosActivos=[
            NinoActivoResponse(
                id=UUID(str(h["id"])),
                nombreCompleto=h["nombreCompleto"],
                edad=h["edad"],
                estadoVisita=h["estadoVisita"],
                horaEntrada=h["horaEntrada"],
                horaSalidaEsperada=h["horaSalidaEsperada"],
                horaSalida=h["horaSalida"],
                minutosTranscurridos=h["minutosTranscurridos"],
                minutosPagados=h["minutosPagados"],
                pulsera=h["pulsera"],
            )
            for h in hijos
        ],
    )
