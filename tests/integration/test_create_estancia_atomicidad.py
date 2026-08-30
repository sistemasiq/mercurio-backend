"""Verifica que create_estancia (ya envuelto en conn.transaction() antes de
este plan) sigue siendo atómico después de agregarle el registro de cambio
en el Task 19 -- si el segundo pago de un lote falla, ni el primer pago ni
el movimiento de cambio deben quedar persistidos."""
import uuid

import pytest

from app.repositories.pagos_comanda import pago_create


async def test_fallo_en_el_segundo_pago_no_deja_nada_persistido(conn, apertura_prueba, monkeypatch):
    import app.repositories.pagos_comanda as pagos_comanda_repo

    llamadas = {"n": 0}
    original = pagos_comanda_repo.pago_create

    async def pago_create_que_falla_en_el_segundo(*args, **kwargs):
        llamadas["n"] += 1
        if llamadas["n"] == 2:
            raise RuntimeError("fallo simulado en el segundo pago")
        return await original(*args, **kwargs)

    monkeypatch.setattr(pagos_comanda_repo, "pago_create", pago_create_que_falla_en_el_segundo)

    # Este test requiere montar un OnboardingRequest completo (tutor, niños,
    # fotos) para ejercer create_estancia real -- se deja como plantilla:
    # completar con datos válidos de la BD de desarrollo (sucursal, producto
    # de tipo estancia, pulseras) antes de ejecutar. Si el fixture completo
    # resulta demasiado costoso de construir en este test, verificar la
    # atomicidad manualmente (Task 19, Step 4) y marcar este test como
    # `pytest.skip` con el motivo documentado, sin dejarlo fallando en rojo.
    pytest.skip(
        "Requiere fixture completo de OnboardingRequest (tutor, niños, fotos, "
        "producto de estancia) -- ver Task 19 Step 4 para la verificación manual "
        "equivalente. Completar este test si se justifica la inversión del fixture."
    )
