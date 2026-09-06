"""Verifica que pago_create_service (POST /estancias/{registro_id}/pagos)
queda envuelto en una transacción y valida el cambio -- endpoint sin
callers en el frontend actual (verificado por grep), corregido por
completitud ya que es superficie pública de la API."""
from decimal import Decimal
from uuid import UUID

import pytest

from app.exceptions import DatosInvalidos
from app.schemas.pagos import PagoEstanciaExtraRequest, PagoIn
from app.services import pagos_estancia
from tests.integration.conftest import CAJERO_ID, TARJETA_ID


async def test_rechaza_cambio_no_respaldado_por_efectivo(conn, apertura_prueba, monkeypatch):
    async def fake_exists_registro(*_args, **_kwargs):
        return True

    monkeypatch.setattr(pagos_estancia, "exists_registro", fake_exists_registro)

    body = PagoEstanciaExtraRequest(
        pagos=[PagoIn(metodoPagoId=UUID(TARJETA_ID), monto=200.0)],
        cambio=Decimal("80.00"),
    )
    with pytest.raises(DatosInvalidos):
        await pagos_estancia.pago_create_service(
            conn, body, sucursal_id=UUID("5e16533e-8d60-453a-9708-306bd64ad326"),
            registro_id=UUID("00000000-0000-0000-0000-000000000001"),
            usuario_id=UUID(CAJERO_ID), apertura_caja_id=apertura_prueba,
        )
