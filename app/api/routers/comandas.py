# app/api/routers/comandas.py
from http.client import HTTPException
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas import comanda as schemas
from app.repositories import comanda_repository
from fastapi import HTTPException
import traceback
from pydantic import BaseModel
router = APIRouter()

class CambioEstadoRequest(BaseModel):
    estado_actual: str  # Debe llamarse igual a la llave que envía el axios

@router.post("/", response_model=schemas.Comanda)
def post_comanda(comanda_in: schemas.ComandaCreate, db: Session = Depends(get_db)):
    print("--- JSON RECIBIDO ---")
    print(comanda_in.dict())
    try:
        return comanda_repository.crear_comanda_con_detalles(db, comanda_in)
    
    except Exception as e:
        print("--- ERROR DETALLADO EN EL BACKEND ---")
        traceback.print_exc() # Esto imprimirá el error completo en tu terminal
        raise HTTPException(status_code=400, detail=str(e))
    
@router.patch("/{comanda_id}/estado")
def cambiar_estado(
    comanda_id: str, 
    data: CambioEstadoRequest,  # Ahora recibe el JSON del cuerpo
    db: Session = Depends(get_db)
):
    # 2. Extrae el valor del objeto 'data'
    comanda_actualizada = comanda_repository.actualizar_estado_comanda(
        db, comanda_id, data.estado_actual
    )
    
    if not comanda_actualizada:
        raise HTTPException(status_code=404, detail="Comanda no encontrada")
        
    return {"message": "Estado actualizado con éxito"}
    
@router.get("/")
def listar_comandas(db: Session = Depends(get_db)):
    # Necesitas importar tu repositorio
    return comanda_repository.get_comandas_pendientes(db)