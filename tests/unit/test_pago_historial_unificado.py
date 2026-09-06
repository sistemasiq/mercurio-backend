import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from app.repositories import pago_repository

SUCURSAL = "22222222-2222-2222-2222-222222222222"


def _fila(tipo_origen: str, referencia: str, titulo: str, metodos_raw):
    return {
        "referencia_id": referencia,
        "tipo_origen": tipo_origen,
        "titulo": titulo,
        "total_final": 120.0,
        "estado_actual": "T",
        "sucursal_id": SUCURSAL,
        "creado": datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
        "creado_por": None,
        "comanda_id": referencia if tipo_origen == "comanda" else None,
        "ticket_numero": titulo if tipo_origen == "comanda" else None,
        "metodos_pago": metodos_raw,
    }


def test_select_historial_une_las_tres_tablas_de_pago():
    sql = pago_repository._SELECT_HISTORIAL
    assert "pagos_ordenes" in sql
    assert "pagos_estancia" in sql
    assert "pagos_reservacion" in sql
    assert "bool_or(v.es_cancelado)" in sql
    assert "'comanda'" in sql and "'estancia'" in sql and "'reservacion'" in sql
    assert "GROUP BY" in sql


def test_select_estadisticas_reusa_el_union_y_excluye_canceladas():
    sql = pago_repository._SELECT_ESTADISTICAS
    assert "pagos_estancia" in sql
    assert "pagos_reservacion" in sql
    assert "NOT v.es_cancelado" in sql


@pytest.mark.asyncio
async def test_historial_agrupa_filas_de_las_tres_fuentes():
    conn = AsyncMock()
    fila_comanda = _fila(
        "comanda",
        "11111111-1111-1111-1111-111111111111",
        "TICKET-1",
        json.dumps([{"metodo_pago_nombre": "Efectivo", "monto": 120.0, "notas_pago": None}]),
    )
    fila_estancia = _fila(
        "estancia",
        "33333333-3333-3333-3333-333333333333",
        "Ana López",
        [{"metodo_pago_nombre": "Tarjeta", "monto": 250.0, "notas_pago": None}],
    )
    fila_reservacion = _fila(
        "reservacion",
        "44444444-4444-4444-4444-444444444444",
        "Carlos Ruiz",
        [{"metodo_pago_nombre": "Efectivo", "monto": 800.0, "notas_pago": "Anticipo"}],
    )
    conn.fetch.return_value = [fila_comanda, fila_estancia, fila_reservacion]

    resultado = await pago_repository.historial(
        conn, SUCURSAL, datetime(2026, 8, 20, 0, 0, tzinfo=UTC), "todos"
    )

    assert len(resultado) == 3
    assert {r["tipo_origen"] for r in resultado} == {"comanda", "estancia", "reservacion"}
    assert resultado[0]["comanda_id"] == "11111111-1111-1111-1111-111111111111"
    assert resultado[1]["comanda_id"] is None
    assert isinstance(resultado[0]["metodos_pago"], list)
    assert resultado[2]["metodos_pago"][0]["metodo_pago_nombre"] == "Efectivo"


@pytest.mark.asyncio
async def test_detalle_por_referencia_estancia():
    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "referencia_id": "33333333-3333-3333-3333-333333333333",
        "titulo": "Ana López",
        "total_final": 250.0,
        "estado_actual": "C",
        "fecha_hora": datetime(2026, 8, 20, 11, 0, tzinfo=UTC),
        "creado_por_nombre": "Juan Pérez",
    }
    conn.fetch.side_effect = [
        [{"metodo_pago_nombre": "Tarjeta", "monto": 250.0, "notas_pago": None}],
        [
            {
                "id": "55555555-5555-5555-5555-555555555555",
                "producto_nombre": "Pulsera",
                "cantidad": 2,
                "precio_unitario": 100.0,
                "importe": 200.0,
                "notas_especiales": "Sofía",
                "nombre_combo_padre": None,
            }
        ],
    ]

    detalle = await pago_repository.detalle_por_referencia(
        conn, "estancia", "33333333-3333-3333-3333-333333333333"
    )

    assert detalle is not None
    assert detalle["tipo_origen"] == "estancia"
    assert detalle["comanda_id"] is None
    assert detalle["titulo"] == "Ana López"
    assert detalle["detalles"][0]["notas_especiales"] == "Sofía"
    assert detalle["metodos_pago"][0]["metodo_pago_nombre"] == "Tarjeta"


@pytest.mark.asyncio
async def test_detalle_por_referencia_reservacion():
    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "referencia_id": "44444444-4444-4444-4444-444444444444",
        "titulo": "Carlos Ruiz",
        "total_final": 800.0,
        "estado_actual": "confirmada",
        "fecha_hora": datetime(2026, 8, 20, 11, 0, tzinfo=UTC),
        "creado_por_nombre": "Juan Pérez",
    }
    conn.fetch.side_effect = [
        [{"metodo_pago_nombre": "Efectivo", "monto": 800.0, "notas_pago": "Anticipo"}],
        [
            {
                "id": "66666666-6666-6666-6666-666666666666",
                "producto_nombre": "Paquete: Cumpleaños",
                "cantidad": 1,
                "precio_unitario": 700.0,
                "importe": 700.0,
                "notas_especiales": None,
                "nombre_combo_padre": None,
            }
        ],
    ]

    detalle = await pago_repository.detalle_por_referencia(
        conn, "reservacion", "44444444-4444-4444-4444-444444444444"
    )

    assert detalle is not None
    assert detalle["tipo_origen"] == "reservacion"
    assert detalle["titulo"] == "Carlos Ruiz"
    assert detalle["detalles"][0]["producto_nombre"].startswith("Paquete:")


@pytest.mark.asyncio
async def test_detalle_por_referencia_comanda_mantiene_ticket():
    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "comanda_id": "11111111-1111-1111-1111-111111111111",
        "ticket_numero": "TICKET-1",
        "total_final": 120.0,
        "estado_actual": "T",
        "fecha_hora": datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
        "motivo_cancelacion": None,
        "creado_por_nombre": "Juan Pérez",
    }
    conn.fetch.side_effect = [
        [{"metodo_pago_nombre": "Efectivo", "monto": 120.0, "notas_pago": None}],
        [
            {
                "id": "77777777-7777-7777-7777-777777777777",
                "producto_nombre": "Hamburguesa",
                "cantidad": 1,
                "precio_unitario": 120.0,
                "importe": 120.0,
                "notas_especiales": None,
                "nombre_combo_padre": None,
            }
        ],
    ]

    detalle = await pago_repository.detalle_por_referencia(
        conn, "comanda", "11111111-1111-1111-1111-111111111111"
    )

    assert detalle is not None
    assert detalle["tipo_origen"] == "comanda"
    assert detalle["comanda_id"] == "11111111-1111-1111-1111-111111111111"
    assert detalle["ticket_numero"] == "TICKET-1"
