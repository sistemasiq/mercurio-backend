from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import asyncpg

from app.core.security import create_access_token
from app.repositories import lealtad_repository
from app.repositories.branch_repository import get_sucursal_by_id
from app.repositories.tutores import get_tutor_by_id
from app.schemas.padres import (
    LealtadPadreInfo,
    NinoActivoResponse,
    PadreDashboardResponse,
    PadreNinosActivosResponse,
    SucursalInfo,
    TutorInfo,
)
from app.services.lealtad_service import DIAS_POR_VENCER
from app.services.permission_service import get_permissions


async def _get_lealtad_tutor(
    conn: asyncpg.Connection, sucursal_id: UUID, telefono: str
) -> LealtadPadreInfo:
    """WP B4, pendiente 5 — saldo de puntos de lealtad del tutor (celular =
    telefono del tutor), para la tarjeta "Tus puntos Woow" del portal de
    padres. No requiere que exista configuracion_lealtad para la sucursal:
    sin movimientos, el saldo simplemente es 0."""
    saldo = await lealtad_repository.calcular_saldo(conn, sucursal_id, telefono)
    por_vencer = await lealtad_repository.calcular_por_vencer(
        conn, sucursal_id, telefono, DIAS_POR_VENCER
    )
    return LealtadPadreInfo(saldo=saldo, por_vencer=por_vencer)


class TokenAccesoInvalidoError(Exception):
    pass


async def _get_hijos_visita(conn: asyncpg.Connection, registro_id: UUID) -> list[dict[str, Any]]:
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
                THEN FLOOR(EXTRACT(EPOCH FROM (NOW() - dr.entrada)) / 60)::int
                ELSE FLOOR(EXTRACT(EPOCH FROM (dr.salida - dr.entrada)) / 60)::int
            END AS "minutosTranscurridos",
            (dr.cantidad * 60)::int AS "minutosPagados",
            p.pulsera_rfid AS "pulsera",
            dr.precio AS "precio",
            dr.cantidad AS "cantidad",
            dr.salida_esperada AS "salidaEsperadaRaw",
            (
                SELECT COALESCE(SUM(ce.total), 0)
                FROM cargos_extra_estancia ce
                WHERE ce.detalles_registro_id = dr.id
            ) AS "cargoExtraCobrado",
            (
                SELECT COALESCE(SUM(mp.puntos), 0)
                FROM movimientos_puntos mp
                WHERE mp.registro_id = r.id AND mp.tipo = 'O'
            ) AS "puntosGanadosRegistro"
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


def _build_nino_activo(hijo: dict[str, Any], now: datetime) -> NinoActivoResponse:
    """Agrega cargoExtra (visita activa) o importe/puntosGanados (visita
    terminada) al DTO de un hijo, reusando la misma fórmula de excedente que
    cotizar_checkout para no desincronizarse de ella (ver chekouts.py)."""
    # Import local para evitar un ciclo: chekouts no importa este módulo.
    from app.services.chekouts import _calcular_cargo_extra_sync

    cargo_extra = 0.0
    importe: float | None = None
    puntos_ganados: int | None = None

    if hijo["estadoVisita"] == "activo":
        _, cargo_extra = _calcular_cargo_extra_sync(hijo["salidaEsperadaRaw"], hijo["precio"], now)
    else:
        importe = float(hijo["precio"]) * hijo["cantidad"] + float(hijo["cargoExtraCobrado"])
        puntos_ganados = int(hijo["puntosGanadosRegistro"])

    return NinoActivoResponse(
        id=UUID(str(hijo["id"])),
        nombreCompleto=hijo["nombreCompleto"],
        edad=hijo["edad"],
        estadoVisita=hijo["estadoVisita"],
        horaEntrada=hijo["horaEntrada"],
        horaSalidaEsperada=hijo["horaSalidaEsperada"],
        horaSalida=hijo["horaSalida"],
        minutosTranscurridos=hijo["minutosTranscurridos"],
        minutosPagados=hijo["minutosPagados"],
        pulsera=hijo["pulsera"],
        cargoExtra=cargo_extra,
        importe=importe,
        puntosGanados=puntos_ganados,
    )


async def get_padre_dashboard(conn: asyncpg.Connection, raw_code: str) -> PadreDashboardResponse:
    try:
        registro_id = UUID(raw_code)
    except ValueError:
        raise TokenAccesoInvalidoError from None

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
        raise TokenAccesoInvalidoError

    tutor = await get_tutor_by_id(conn, registro["tutorId"])
    if tutor is None:
        raise TokenAccesoInvalidoError

    sucursal = await get_sucursal_by_id(conn, registro["sucursalId"])
    if sucursal is None:
        raise TokenAccesoInvalidoError

    hijos = await _get_hijos_visita(conn, registro_id)
    now = datetime.now(UTC)
    lealtad = await _get_lealtad_tutor(conn, sucursal["id"], tutor["telefono"])

    expires_delta = timedelta(hours=2)
    access_token = create_access_token(
        payload={
            "sub": str(registro_id),
            "email": f"{tutor['telefono']}@tutor.woowkids.local",
            "tutor_id": str(tutor["id"]),
            "branch_id": str(sucursal["id"]),
            "role": "PadreVisor",
            "permissions": get_permissions("PadreVisor"),
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
            lealtad=lealtad,
        ),
        ninosActivos=[_build_nino_activo(h, now) for h in hijos],
    )


async def get_ninos_activos(
    conn: asyncpg.Connection, registro_id: UUID
) -> PadreNinosActivosResponse:
    """QA #31 — polling autenticado con el token de sesión del padre (no vuelve
    a canjear el código). Si el registro ya no está activo (p. ej. se cerró o
    se revocó), el token deja de servir: el front recibe 400 y cierra sesión."""
    registro = await conn.fetchrow(
        "SELECT 1 FROM registros WHERE id = $1 AND activo = TRUE AND estado = 'A'",
        registro_id,
    )
    if registro is None:
        raise TokenAccesoInvalidoError

    hijos = await _get_hijos_visita(conn, registro_id)
    now = datetime.now(UTC)
    return PadreNinosActivosResponse(ninosActivos=[_build_nino_activo(h, now) for h in hijos])
