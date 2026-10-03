"""Pendiente B9 A: los bloques de disponibilidad respetan el horario de
operación de la sucursal (hora_apertura / hora_cierre), no un horario fijo."""

from datetime import time
from uuid import uuid4

from app.services.disponibilidad import generar_bloques


def test_genera_bloques_con_horario_no_default():
    bloques = generar_bloques(time(10, 0), time(13, 0), reservaciones=[])

    assert [b.hora_inicio for b in bloques] == [time(10, 0), time(11, 0), time(12, 0)]
    assert [b.hora_fin for b in bloques] == [time(11, 0), time(12, 0), time(13, 0)]
    assert all(not b.ocupado for b in bloques)


def test_marca_bloque_ocupado_cuando_reservacion_se_traslapa():
    reservaciones = [{"id": uuid4(), "hora_inicio": time(11, 30), "hora_fin": time(12, 30)}]

    bloques = generar_bloques(time(10, 0), time(13, 0), reservaciones=reservaciones)

    ocupados = [b for b in bloques if b.ocupado]
    assert len(ocupados) == 2
    assert {b.hora_inicio for b in ocupados} == {time(11, 0), time(12, 0)}
