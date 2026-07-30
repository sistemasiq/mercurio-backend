from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

import asyncpg

from app.core.security import create_access_token
from app.repositories.branch_repository import get_sucursal_by_id
from app.repositories.padres_token_repository import validate_padres_token
from app.repositories.tutores import get_tutor_by_id
from app.schemas.padres import (
    NinoActivoResponse,
    PadreDashboardResponse,
    SucursalInfo,
    TutorInfo,
)


class TokenAccesoInvalido(Exception):
    pass


async def _get_hijos_activos(
    conn: asyncpg.Connection, tutor_id: UUID
) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT
            n.id,
            n.nombre_completo AS "nombreCompleto",
            n.edad,
            'activo' AS "estadoVisita",
            dr.entrada AS "horaEntrada",
            dr.salida_esperada AS "horaSalidaEsperada",
            FLOOR(EXTRACT(EPOCH FROM (NOW() - dr.entrada)) / 60)::int
                AS "minutosTranscurridos",
            (dr.cantidad * 60)::int AS "minutosPagados",
            p.pulsera_rfid AS "pulsera"
        FROM detalles_registro dr
        JOIN registros r ON r.id = dr.registros_id
        JOIN ninos n ON n.id = dr.ninos_id
        JOIN pulseras p ON p.id = dr.pulseras_id
        WHERE r.tutores_id = $1
          AND r.estado = 'A'
          AND dr.salida IS NULL
          AND dr.activo = TRUE
        ORDER BY dr.entrada
        """,
        tutor_id,
    )
    return [dict(r) for r in rows]


async def get_padre_dashboard(
    conn: asyncpg.Connection, raw_token: str
) -> PadreDashboardResponse:
    token_uuid = UUID(raw_token)

    payload = await validate_padres_token(conn, token_uuid)
    if payload is None:
        raise TokenAccesoInvalido

    tutor_id = payload["tutor_id"]
    sucursal_id = payload["sucursal_id"]

    tutor = await get_tutor_by_id(conn, tutor_id)
    if tutor is None:
        raise TokenAccesoInvalido

    sucursal = await get_sucursal_by_id(conn, sucursal_id)
    if sucursal is None:
        raise TokenAccesoInvalido

    hijos = await _get_hijos_activos(conn, tutor_id)

    expires_delta = timedelta(hours=2)
    access_token = create_access_token(
        payload={
            "sub": str(tutor_id),
            "sucursal_id": str(sucursal_id),
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
        ),
        ninosActivos=[
            NinoActivoResponse(
                id=UUID(str(h["id"])),
                nombreCompleto=h["nombreCompleto"],
                edad=h["edad"],
                estadoVisita=h["estadoVisita"],
                horaEntrada=h["horaEntrada"],
                horaSalidaEsperada=h["horaSalidaEsperada"],
                minutosTranscurridos=h["minutosTranscurridos"],
                minutosPagados=h["minutosPagados"],
                pulsera=h["pulsera"],
            )
            for h in hijos
        ],
    )
