# TODO: migrar de SQLAlchemy a asyncpg (ver CLAUDE.md — no ORM)
from typing import Any

from sqlalchemy.orm import Session  # type: ignore[import-not-found]

from app.models.producto import Producto


def get_productos_activos(db: Session) -> Any:
    return db.query(Producto).filter(Producto.activo == True).all()  # noqa: E712
