"""Verifica que el detalle de arqueo expone los movimientos de cambio del
turno, con el mismo nivel de trazabilidad que ya tienen los retiros
parciales."""
import json
import uuid
from decimal import Decimal

import pytest_asyncio

from app.repositories import caja_repository
from app.services import turnos_caja_service


@pytest_asyncio.fixture
async def cierre_con_cambio(conn, apertura_prueba):
    """Crea un cierre confirmado sobre la apertura de prueba, con un
    movimiento de cambio ya registrado, y lo limpia al terminar."""
    await caja_repository.registrar_cambio_caja(
        conn, apertura_caja_id=apertura_prueba, referencia_id=str(uuid.uuid4()), monto=Decimal("80.00")
    )
    await caja_repository.actualizar_conteo_apertura(
        conn, apertura_prueba, Decimal("1000.00"),
        json.dumps({"desglose_efectivo": {"total": 1000.00}, "metodos_pago": []}),
    )
    apertura = await caja_repository.get_apertura_por_id(conn, apertura_prueba)
    cierre = await caja_repository.crear_cierre_caja(
        conn,
        apertura_caja_id=apertura_prueba,
        tipo_cierre="NORMAL",
        monto_sistema=Decimal("1000.00"),
        monto_cierre=Decimal("1000.00"),
        cajero_id=str(apertura["cajero_id"]),
        administrador_id=str(apertura["cajero_id"]),
        observaciones=None,
    )
    cierre_id = str(cierre["id"])
    yield cierre_id
    await conn.execute("DELETE FROM public.cierre_caja WHERE id = $1", uuid.UUID(cierre_id))


async def test_detalle_arqueo_incluye_los_cambios_del_turno(conn, cierre_con_cambio):
    detalle = await turnos_caja_service.obtener_detalle(conn, cierre_con_cambio)
    assert len(detalle.cambios) == 1
    assert detalle.cambios[0].monto == Decimal("80.00")
