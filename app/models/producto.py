# TODO: migrar de SQLAlchemy a asyncpg (ver CLAUDE.md — no ORM)
from app.core.database import Base  # type: ignore[attr-defined]
from sqlalchemy import Boolean, Column, DateTime, Numeric, String  # type: ignore[import-not-found]
from sqlalchemy.sql import func  # type: ignore[import-not-found]


class Producto(Base):  # type: ignore[misc]
    __tablename__ = "productos"

    id = Column(String, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    tipo = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)
    imagen = Column(String(255), nullable=True)
    sucursal_id = Column(String, nullable=False)
    activo = Column(Boolean, default=True)
    creado = Column(DateTime(timezone=True), server_default=func.now())
    creado_por = Column(String, nullable=True)
    modificado = Column(DateTime(timezone=True), nullable=True)
    modificado_por = Column(String, nullable=True)
