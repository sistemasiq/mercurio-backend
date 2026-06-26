from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories import producto_repository

router = APIRouter()

@router.get("/")
def listar_productos(db: Session = Depends(get_db)):
    return producto_repository.get_productos_activos(db)