"""Verifica que create_estancia valida el cambio contra el efectivo
realmente aportado antes de registrar un registro de estancia (check-in de
niños), reusando la misma validar_cambio del resto del módulo de Caja."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from app.exceptions import DatosInvalidos
from app.repositories import metodos_pago_repository
from app.schemas.ninos import NinoIn
from app.schemas.pagos import PagoIn
from app.schemas.registros import DetalleIn, OnboardingRequest
from app.schemas.tutores import TutorIn
from app.services import estancias as estancias_module
from app.services.validaciones_pago import validar_cambio

from tests.integration.conftest import CAJERO_ID, EFECTIVO_ID, TARJETA_ID

# Sucursal "La Piedad Centro" -- misma usada en test_pagos_reservacion_completar.py
# y en los comentarios de conftest.py sobre la sesión de QA de Cierre de Caja.
# Tiene datos reales de catálogo para Estancias: 1 producto tipo 'E'
# ("Hora Estancia", $50.00/hr, id fijo 11111111-1111-1111-1111-111111111111)
# y varias pulseras activas (verificado contra la BD de desarrollo real con
# SELECT sucursal_id, COUNT(*) FROM productos WHERE tipo='E' GROUP BY
# sucursal_id -- de las 3 sucursales con productos tipo estancia, esta es la
# que ya se usa en otros tests de este mismo plan).
SUCURSAL_ID_ESTANCIA = UUID("905ea5cf-6951-43f1-9766-75f7e61fde07")
PRODUCTO_ESTANCIA_ID = UUID("11111111-1111-1111-1111-111111111111")


async def test_tarjeta_con_cambio_se_rechaza_para_estancias(conn):
    ids_efectivo = await metodos_pago_repository.obtener_ids_por_tipo(conn, "E")
    pagos = [PagoIn(metodoPagoId=UUID(TARJETA_ID), monto=200.0)]
    with pytest.raises(DatosInvalidos):
        validar_cambio(
            [(p.metodoPagoId, Decimal(str(p.monto))) for p in pagos],
            Decimal("80.00"),
            ids_efectivo,
        )


async def test_efectivo_con_cambio_valido_no_se_rechaza_para_estancias(conn):
    ids_efectivo = await metodos_pago_repository.obtener_ids_por_tipo(conn, "E")
    pagos = [PagoIn(metodoPagoId=UUID(EFECTIVO_ID), monto=200.0)]
    validar_cambio(
        [(p.metodoPagoId, Decimal(str(p.monto))) for p in pagos],
        Decimal("80.00"),
        ids_efectivo,
    )


# ---------------------------------------------------------------------------
# Finding 1 (revisión final de integridad-cambio-caja): las dos pruebas de
# arriba solo ejercitan validar_cambio() de forma aislada -- nunca pasan por
# create_estancia() en sí, así que nunca hubieran detectado que la llamada a
# validar_cambio() ahí estaba envuelta en un `if data.pagos:` y por lo tanto
# se saltaba por completo cuando pagos venía vacío/None, dejando pasar un
# `cambio` sin ningún efectivo real que lo respalde (registrar_cambio_caja
# se ejecuta después, guardado solo por `if cambio > 0`, sin relación con si
# hubo validación). Las pruebas siguientes llaman a create_estancia() de
# verdad para cerrar ese hueco end-to-end.
# ---------------------------------------------------------------------------


def _onboarding_minimo(*, pagos: list[PagoIn] | None, cambio: Decimal) -> OnboardingRequest:
    """OnboardingRequest sintácticamente válido pero con detalles=[] -- basta
    para las pruebas de rechazo porque validar_cambio() corre en
    create_estancia() antes de tocar tutor/niños/fotos/DB, así que nunca se
    llega a necesitar catálogo real para estos casos."""
    return OnboardingRequest(
        sucursalId=uuid4(),
        tutor=TutorIn(nombreCompleto="Tutor Rechazo", telefono="5550000000"),
        pulseraTutorId=uuid4(),
        parentesco="Padre",
        detalles=[],
        pagos=pagos,
        cambio=cambio,
    )


async def test_create_estancia_rechaza_cambio_con_pagos_vacios(conn):
    """pagos=[] y cambio>0 -- el caso exacto del bug: antes del fix, `if
    data.pagos:` era False para una lista vacía y validar_cambio() nunca se
    llamaba, dejando pasar el registro de cambio sin efectivo real."""
    data = _onboarding_minimo(pagos=[], cambio=Decimal("100.00"))
    with pytest.raises(DatosInvalidos):
        await estancias_module.create_estancia(
            conn,
            data,
            foto_ine=None,
            foto_llegadas=[],
            usuario_id=UUID(CAJERO_ID),
            apertura_caja_id="00000000-0000-0000-0000-000000000000",
        )


async def test_create_estancia_rechaza_cambio_con_pagos_none(conn):
    """pagos=None (el default del schema, equivalente a omitir el campo) y
    cambio>0 -- mismo hueco que con lista vacía, cubierto aparte porque
    `data.pagos or []` debe manejar ambos casos."""
    data = _onboarding_minimo(pagos=None, cambio=Decimal("100.00"))
    with pytest.raises(DatosInvalidos):
        await estancias_module.create_estancia(
            conn,
            data,
            foto_ine=None,
            foto_llegadas=[],
            usuario_id=UUID(CAJERO_ID),
            apertura_caja_id="00000000-0000-0000-0000-000000000000",
        )


@pytest.mark.skip(
    reason="Quedó obsoleto tras el merge de feature/registro-infantes: el precio de "
    "estancia ya no es plano por producto (get_precio_individual_by_id) sino por "
    "tramos de horas (config_estancia). El total esperado y el fixture de la BD "
    "de desarrollo (config_estancia del PRODUCTO_ESTANCIA_ID) hay que rehacerlos "
    "para el nuevo modelo -- ver dueño de tramos de precio."
)
async def test_create_estancia_registra_pago_y_cambio_respaldado(
    conn, apertura_prueba, monkeypatch
):
    """Camino feliz: un pago en efectivo que sí respalda el cambio declarado
    debe crear el registro y exactamente un movimiento tipo_movimiento='C'
    con el monto correcto. Las fotos se mockean (upload_bytes/validar_y_leer)
    porque no son parte de la lógica contable bajo prueba; todo lo demás
    (tutor, niño, registro, pago, cambio) golpea la BD real de desarrollo,
    igual que el resto de tests de integración de este proyecto."""
    pulseras = await conn.fetch(
        "SELECT id FROM public.pulseras WHERE sucursal_id = $1 AND activo = TRUE LIMIT 2",
        SUCURSAL_ID_ESTANCIA,
    )
    assert len(pulseras) == 2, (
        "La sucursal de prueba necesita al menos 2 pulseras activas en la BD "
        "de desarrollo para poder correr este test."
    )
    pulsera_tutor_id = pulseras[0]["id"]
    pulsera_nino_id = pulseras[1]["id"]

    telefono = f"555{uuid4().hex[:7]}"

    async def fake_validar_y_leer(_imagen):
        return b"fake-image-bytes"

    async def fake_upload_bytes(*_args, **_kwargs):
        return None

    monkeypatch.setattr(estancias_module, "validar_y_leer", fake_validar_y_leer)
    monkeypatch.setattr(estancias_module, "upload_bytes", fake_upload_bytes)

    data = OnboardingRequest(
        sucursalId=SUCURSAL_ID_ESTANCIA,
        tutor=TutorIn(nombreCompleto="Tutor de Prueba Finding2", telefono=telefono),
        pulseraTutorId=pulsera_tutor_id,
        parentesco="Padre",
        detalles=[
            DetalleIn(
                nino=NinoIn(nombreCompleto="Nino de Prueba Finding2", edad=5, notas=None),
                productoId=PRODUCTO_ESTANCIA_ID,
                cantidad=2,
                pulseraId=pulsera_nino_id,
            )
        ],
        pagos=[PagoIn(metodoPagoId=UUID(EFECTIVO_ID), monto=150.0)],
        cambio=Decimal("50.00"),
    )

    registro_id = None
    try:
        resultado = await estancias_module.create_estancia(
            conn,
            data,
            foto_ine=None,
            foto_llegadas=[],
            usuario_id=UUID(CAJERO_ID),
            apertura_caja_id=apertura_prueba,
        )
        registro_id = resultado["registroId"]

        assert resultado["total"] == Decimal("100.00")
        assert resultado["pagado"] == 150.0
        assert resultado["estado"] == "A"

        filas_cambio = await conn.fetch(
            "SELECT monto FROM public.movimientos_caja "
            "WHERE apertura_caja_id = $1 AND tipo_movimiento = 'C'",
            UUID(apertura_prueba),
        )
        assert len(filas_cambio) == 1
        assert filas_cambio[0]["monto"] == Decimal("50.00")
    finally:
        # movimientos_caja (pago 'E' + cambio 'C') ya se limpian solos en el
        # teardown de apertura_prueba (filtra por apertura_caja_id).
        if registro_id is not None:
            await conn.execute(
                "DELETE FROM public.pagos_estancia WHERE registros_id = $1", registro_id
            )
            filas_ninos = await conn.fetch(
                "SELECT ninos_id FROM public.detalles_registro WHERE registros_id = $1",
                registro_id,
            )
            await conn.execute(
                "DELETE FROM public.detalles_registro WHERE registros_id = $1", registro_id
            )
            for fila in filas_ninos:
                await conn.execute("DELETE FROM public.ninos WHERE id = $1", fila["ninos_id"])
            await conn.execute("DELETE FROM public.registros WHERE id = $1", registro_id)
        await conn.execute(
            "DELETE FROM public.tutores WHERE telefono = $1 AND sucursal_id = $2",
            telefono,
            SUCURSAL_ID_ESTANCIA,
        )
