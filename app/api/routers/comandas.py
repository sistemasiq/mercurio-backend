# app/api/routers/comandas.py
# TODO: migrar de SQLAlchemy a asyncpg (ver CLAUDE.md — no ORM)
import traceback

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session  # type: ignore[import-not-found]

from app.core.database import get_db
from app.repositories import comanda_repository
from app.schemas import comanda as schemas

router = APIRouter()


class CambioEstadoRequest(BaseModel):
    estado_actual: str


@router.post("/", response_model=schemas.Comanda)
def post_comanda(comanda_in: schemas.ComandaCreate, db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
    print("--- JSON RECIBIDO ---")
    print(comanda_in.dict())
    try:
        return comanda_repository.crear_comanda_con_detalles(db, comanda_in)
    except Exception as e:
        print("--- ERROR DETALLADO EN EL BACKEND ---")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/{comanda_id}/estado")
def cambiar_estado(  # type: ignore[no-untyped-def]
    comanda_id: str,
    data: CambioEstadoRequest,
    db: Session = Depends(get_db),
):
    comanda_actualizada = comanda_repository.actualizar_estado_comanda(
        db, comanda_id, data.estado_actual
    )
    if not comanda_actualizada:
        raise HTTPException(status_code=404, detail="Comanda no encontrada")
    return {"message": "Estado actualizado con éxito"}


@router.get("/")
def listar_comandas(db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
    return comanda_repository.get_comandas_pendientes(db)
