# TODO: migrar de SQLAlchemy a asyncpg (ver CLAUDE.md — no ORM)
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # type: ignore[import-not-found]

from app.core.database import get_db
from app.repositories import producto_repository

router = APIRouter()


@router.get("/")
def listar_productos(db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
    return producto_repository.get_productos_activos(db)
