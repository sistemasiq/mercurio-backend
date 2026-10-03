"""Disponibilidad por bloque de horario para una sucursal y fecha -- pendiente
"Bloques de horario ocupados o libres" de docs/pendientes-backend.md."""

from datetime import date, time
from typing import Any
from uuid import UUID

import asyncpg

from app.repositories import reservaciones_repository
from app.repositories.branch_repository import get_horario_operacion
from app.schemas.disponibilidad import BloqueDisponibilidad, DisponibilidadResponse

# Horario comercial por defecto, usado solo si la sucursal no se encuentra
# (no debería pasar en uso normal, ya que el endpoint recibe un sucursal_id
# válido). El horario real de cada sucursal vive en sucursales.hora_apertura
# / hora_cierre (ver migración 070).
HORA_APERTURA = time(9, 0)
HORA_CIERRE = time(23, 0)
DURACION_BLOQUE_HORAS = 1


def _sumar_horas(t: time, horas: int) -> time:
    minutos_totales = t.hour * 60 + t.minute + horas * 60
    return time((minutos_totales // 60) % 24, minutos_totales % 60)


def generar_bloques(
    hora_apertura: time,
    hora_cierre: time,
    reservaciones: list[Any],
    duracion_horas: int = DURACION_BLOQUE_HORAS,
) -> list[BloqueDisponibilidad]:
    """Genera los bloques de `duracion_horas` entre `hora_apertura` y
    `hora_cierre`, marcados como ocupados según las reservaciones que se
    traslapen con cada bloque. No soporta cruce de medianoche: se asume
    hora_apertura < hora_cierre."""
    bloques: list[BloqueDisponibilidad] = []
    inicio = hora_apertura
    while inicio < hora_cierre:
        fin = _sumar_horas(inicio, duracion_horas)
        ocupante = next(
            (r for r in reservaciones if r["hora_inicio"] < fin and r["hora_fin"] > inicio),
            None,
        )
        bloques.append(
            BloqueDisponibilidad(
                hora_inicio=inicio,
                hora_fin=fin,
                ocupado=ocupante is not None,
                reservacion_id=ocupante["id"] if ocupante else None,
            )
        )
        inicio = fin
    return bloques


async def obtener_disponibilidad(
    conn: asyncpg.Connection, sucursal_id: UUID, fecha: date
) -> DisponibilidadResponse:
    """Bloques del horario de operación de la sucursal para `fecha`, marcados
    como ocupados o libres según las reservaciones no canceladas que se
    traslapen con cada bloque."""
    horario = await get_horario_operacion(conn, sucursal_id)
    hora_apertura = horario["hora_apertura"] if horario else HORA_APERTURA
    hora_cierre = horario["hora_cierre"] if horario else HORA_CIERRE

    reservaciones = await reservaciones_repository.listar_por_sucursal_y_fecha(
        conn, sucursal_id, fecha
    )

    bloques = generar_bloques(hora_apertura, hora_cierre, reservaciones)

    return DisponibilidadResponse(sucursal_id=sucursal_id, fecha=fecha.isoformat(), bloques=bloques)
