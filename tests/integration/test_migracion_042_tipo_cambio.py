"""Verifica que la migración 042 agregó el tipo 'C' (Cambio) al enum
tipo_movimiento_caja. La lista completa de valores conocidos (incluyendo los
agregados por migraciones posteriores) se documenta en
test_migracion_043_tipo_ingreso.py."""


async def test_enum_tipo_movimiento_caja_incluye_cambio(conn):
    rows = await conn.fetch(
        """
        SELECT enumlabel FROM pg_enum
        WHERE enumtypid = 'public.tipo_movimiento_caja'::regtype
        ORDER BY enumsortorder
        """
    )
    valores = [r["enumlabel"] for r in rows]
    # Contención, no igualdad exacta: la BD compartida de desarrollo puede tener
    # valores extra de ramas aún no integradas. Lo que esta migración garantiza
    # es que 'C' (042) y 'RP' (045) existan, y que 'RP' quede antes de 'C' para
    # coincidir con app/models/caja.py::TipoMovimientoCaja.
    for esperado in ("E", "O", "R", "RP", "C"):
        assert esperado in valores, f"falta {esperado!r} en el enum: {valores}"
    assert valores.index("RP") < valores.index("C")
