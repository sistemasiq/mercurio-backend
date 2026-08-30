"""Verifica pagos_reservacion.completar(): agrupa N pagos + 1 cambio en una
transacción atómica, en vez del loop de requests sueltos que hacía
CierreEventoPage.vue/NuevaReservacionPage.vue antes de este fix."""

import uuid
from decimal import Decimal
from uuid import UUID

import pytest
import pytest_asyncio
from app.exceptions import DatosInvalidos
from app.schemas.pagos_reservacion import PagoReservacionItem, PagosReservacionCompletarRequest
from app.services import pagos_reservacion

from tests.integration.conftest import CAJERO_ID, EFECTIVO_ID, TARJETA_ID

# NOTA: el brief original de este task usaba la sucursal de la fixture
# apertura_prueba (5e16533e-8d60-453a-9708-306bd64ad326, "QA Regresion
# BUG-P01") también como sucursal de la reservación. Verificado contra la BD
# de desarrollo real: esa sucursal tiene 0 filas en tipos_evento y 0 en
# paquetes (confirmado con SELECT COUNT(*) ... GROUP BY sucursal_id sobre
# todas las sucursales), así que el fixture reservacion_prueba abajo no
# podría resolver tipo_evento_id/paquete_id ahí y su propio assert fallaría.
# Se usa en su lugar "La Piedad Centro" (905ea5cf-6951-43f1-9766-75f7e61fde07),
# que sí tiene datos reales (3 tipos_evento, 7 paquetes) -- misma sucursal
# referenciada en los comentarios de conftest.py sobre la sesión de QA de
# Cierre de Caja. completar()/crear() no validan que la reservación y la
# caja de la apertura compartan sucursal (ese scope check solo vive en
# listar_por_reservacion, no en completar()), así que usar una sucursal
# distinta para la reservación que la de CAJA_ID/apertura_prueba no afecta
# el comportamiento bajo prueba.
SUCURSAL_ID_RESERVACION = "905ea5cf-6951-43f1-9766-75f7e61fde07"


@pytest_asyncio.fixture
async def reservacion_prueba(conn):
    """Reservación desechable mínima para probar pagos -- se limpia (pagos +
    reservación) al terminar, incluso si el test falla a medias.
    tipo_evento_id y paquete_id son FK NOT NULL sin default (esquema en
    sql/migrations/014_eventos_reservaciones.sql): se resuelven contra un
    tipo de evento y un paquete ya existentes en la sucursal de prueba, en
    vez de inventar ids que no existirían en la BD compartida real."""
    tipo_evento_id = await conn.fetchval(
        "SELECT id FROM public.tipos_evento WHERE sucursal_id = $1 LIMIT 1",
        uuid.UUID(SUCURSAL_ID_RESERVACION),
    )
    paquete_id = await conn.fetchval(
        "SELECT id FROM public.paquetes WHERE sucursal_id = $1 LIMIT 1",
        uuid.UUID(SUCURSAL_ID_RESERVACION),
    )
    assert tipo_evento_id and paquete_id, (
        "La sucursal de prueba necesita al menos un tipo_evento y un paquete "
        "ya creados en la BD de desarrollo para poder correr este fixture."
    )
    row = await conn.fetchrow(
        """
        INSERT INTO public.reservaciones
            (sucursal_id, tipo_evento_id, paquete_id, nombre_cliente, telefono_cliente,
             fecha_evento, hora_inicio, hora_fin, numero_personas, precio_base,
             precio_total, estado)
        VALUES ($1, $2, $3, 'Cliente de prueba', '5555555555',
                CURRENT_DATE, '10:00', '14:00', 5, 500.00, 500.00, 'confirmada')
        RETURNING id
        """,
        uuid.UUID(SUCURSAL_ID_RESERVACION),
        tipo_evento_id,
        paquete_id,
    )
    reservacion_id = str(row["id"])
    try:
        yield reservacion_id
    finally:
        # crear() (Task 3, reusado por completar()) también otorga puntos de
        # lealtad vía lealtad_service.otorgar_puntos cuando la reservación
        # trae telefono_cliente y la sucursal tiene el programa activo --
        # confirmado en la práctica: la sucursal usada aquí (La Piedad
        # Centro) sí lo tiene activo, a diferencia de la sucursal de la
        # apertura_prueba original del brief. Eso deja filas en lotes_puntos
        # / movimientos_puntos referenciando esta reservación (FKs sin
        # ON DELETE CASCADE, ver sql/migrations/035_lealtad_reservaciones.sql)
        # que deben limpiarse antes del DELETE de reservaciones o este
        # teardown revienta con ForeignKeyViolationError.
        await conn.execute(
            "DELETE FROM public.movimientos_puntos WHERE reservacion_id = $1 "
            "OR lote_id IN (SELECT id FROM public.lotes_puntos WHERE reservacion_id = $1)",
            uuid.UUID(reservacion_id),
        )
        await conn.execute(
            "DELETE FROM public.lotes_puntos WHERE reservacion_id = $1",
            uuid.UUID(reservacion_id),
        )
        await conn.execute(
            "DELETE FROM public.movimientos_caja WHERE referencia_id IN "
            "(SELECT id FROM public.pagos_reservacion WHERE reservacion_id = $1) "
            "OR (referencia_id = $1 AND tipo_movimiento = 'C')",
            uuid.UUID(reservacion_id),
        )
        await conn.execute(
            "DELETE FROM public.pagos_reservacion WHERE reservacion_id = $1",
            uuid.UUID(reservacion_id),
        )
        await conn.execute(
            "DELETE FROM public.reservaciones WHERE id = $1", uuid.UUID(reservacion_id)
        )


async def test_completar_registra_multiples_pagos_y_el_cambio(
    conn, apertura_prueba, reservacion_prueba
):
    body = PagosReservacionCompletarRequest(
        reservacion_id=UUID(reservacion_prueba),
        pagos=[
            PagoReservacionItem(metodo_pago_id=UUID(TARJETA_ID), monto=Decimal("50.00")),
            PagoReservacionItem(metodo_pago_id=UUID(EFECTIVO_ID), monto=Decimal("150.00")),
        ],
        cambio=Decimal("80.00"),
    )

    resultado = await pagos_reservacion.completar(conn, body, UUID(CAJERO_ID), apertura_prueba)

    assert len(resultado.pagos) == 2
    assert resultado.cambio == Decimal("80.00")

    fila_cambio = await conn.fetchrow(
        "SELECT monto FROM public.movimientos_caja "
        "WHERE apertura_caja_id = $1 AND tipo_movimiento = 'C'",
        uuid.UUID(apertura_prueba),
    )
    assert fila_cambio["monto"] == Decimal("80.00")


async def test_completar_rechaza_cambio_no_respaldado_por_efectivo(
    conn, apertura_prueba, reservacion_prueba
):
    body = PagosReservacionCompletarRequest(
        reservacion_id=UUID(reservacion_prueba),
        pagos=[PagoReservacionItem(metodo_pago_id=UUID(TARJETA_ID), monto=Decimal("200.00"))],
        cambio=Decimal("80.00"),
    )
    with pytest.raises(DatosInvalidos):
        await pagos_reservacion.completar(conn, body, UUID(CAJERO_ID), apertura_prueba)

    # Nada debe haberse persistido: la validación corre antes de abrir la transacción.
    pagos = await conn.fetch(
        "SELECT 1 FROM public.pagos_reservacion WHERE reservacion_id = $1",
        UUID(reservacion_prueba),
    )
    assert len(pagos) == 0


async def test_completar_falla_a_mitad_no_deja_pagos_parciales(
    conn, apertura_prueba, reservacion_prueba, monkeypatch
):
    """Si el segundo pago de un lote falla, el primero tampoco debe quedar
    persistido -- la transacción atómica es el punto de este task."""
    from app.repositories import pagos_reservacion_repository

    llamadas = {"n": 0}
    original = pagos_reservacion_repository.crear

    async def crear_que_falla_en_el_segundo(*args, **kwargs):
        llamadas["n"] += 1
        if llamadas["n"] == 2:
            raise RuntimeError("fallo simulado en el segundo pago")
        return await original(*args, **kwargs)

    monkeypatch.setattr(pagos_reservacion_repository, "crear", crear_que_falla_en_el_segundo)

    body = PagosReservacionCompletarRequest(
        reservacion_id=UUID(reservacion_prueba),
        pagos=[
            PagoReservacionItem(metodo_pago_id=UUID(EFECTIVO_ID), monto=Decimal("100.00")),
            PagoReservacionItem(metodo_pago_id=UUID(EFECTIVO_ID), monto=Decimal("100.00")),
        ],
        cambio=Decimal("0"),
    )
    with pytest.raises(RuntimeError):
        await pagos_reservacion.completar(conn, body, UUID(CAJERO_ID), apertura_prueba)

    pagos = await conn.fetch(
        "SELECT 1 FROM public.pagos_reservacion WHERE reservacion_id = $1",
        UUID(reservacion_prueba),
    )
    assert len(pagos) == 0  # el rollback deshizo el primer pago también
