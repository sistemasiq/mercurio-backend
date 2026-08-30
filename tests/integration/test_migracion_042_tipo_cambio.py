"""Verifica que la migración 042 agregó el tipo 'C' (Cambio) al enum
tipo_movimiento_caja."""


async def test_enum_tipo_movimiento_caja_incluye_cambio(conn):
    rows = await conn.fetch(
        """
        SELECT enumlabel FROM pg_enum
        WHERE enumtypid = 'public.tipo_movimiento_caja'::regtype
        ORDER BY enumsortorder
        """
    )
    valores = [r["enumlabel"] for r in rows]
    assert valores == ["E", "O", "R", "RP", "C"]
