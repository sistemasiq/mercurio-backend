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
    assert "C" in valores
