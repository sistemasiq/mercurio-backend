"""Disponibilidad por bloque de horario para una sucursal y fecha -- pendiente
"Bloques de horario ocupados o libres" de docs/pendientes-backend.md."""

from datetime import date, time
from uuid import UUID

import asyncpg

from app.repositories import reservaciones_repository
from app.schemas.disponibilidad import BloqueDisponibilidad, DisponibilidadResponse

# No existe todavía un modelo de horario de apertura/cierre por sucursal en el
# esquema -- la única tabla "horarios" son los turnos de caja (ver
# app/repositories/horarios_repository.py), un concepto distinto. Mientras no
# se defina uno, se usa un horario comercial fijo en bloques de una hora.
HORA_APERTURA = time(9, 0)
HORA_CIERRE = time(23, 0)
DURACION_BLOQUE_HORAS = 1


def _sumar_horas(t: time, horas: int) -> time:
    minutos_totales = t.hour * 60 + t.minute + horas * 60
    return time((minutos_totales // 60) % 24, minutos_totales % 60)


async def obtener_disponibilidad(
    conn: asyncpg.Connection, sucursal_id: UUID, fecha: date
) -> DisponibilidadResponse:
    """Bloques de horario comercial de la sucursal para `fecha`, marcados como
    ocupados o libres según las reservaciones no canceladas que se traslapen
    con cada bloque."""
    reservaciones = await reservaciones_repository.listar_por_sucursal_y_fecha(
        conn, sucursal_id, fecha
    )

    bloques: list[BloqueDisponibilidad] = []
    inicio = HORA_APERTURA
    while inicio < HORA_CIERRE:
        fin = _sumar_horas(inicio, DURACION_BLOQUE_HORAS)
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

    return DisponibilidadResponse(sucursal_id=sucursal_id, fecha=fecha.isoformat(), bloques=bloques)
