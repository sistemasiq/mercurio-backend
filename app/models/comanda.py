# app/models/comanda.py
# TODO: migrar de SQLAlchemy a asyncpg (ver CLAUDE.md — no ORM)
from app.core.database import Base  # type: ignore[attr-defined]
from app.models.enums import EstadoComanda
from sqlalchemy import (  # type: ignore[import-not-found]
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
)
from sqlalchemy.orm import relationship  # type: ignore[import-not-found]
from sqlalchemy.sql import func  # type: ignore[import-not-found]


class Comanda(Base):  # type: ignore[misc]
    __tablename__ = "comandas"

    id = Column(String, primary_key=True, index=True)
    ticket_numero = Column(String(10), nullable=False)
    fecha_hora = Column(DateTime(timezone=True), server_default=func.now())
    estado_actual = Column(String, default=EstadoComanda.PENDIENTE.value, nullable=False)
    total_final = Column(Numeric(10, 2), default=0.00)
    sucursal_id = Column(String, nullable=False)

    detalles = relationship("DetalleComanda", back_populates="comanda")


class DetalleComanda(Base):  # type: ignore[misc]
    __tablename__ = "detalles_comanda"

    id = Column(String, primary_key=True, index=True)
    comanda_id = Column(String, ForeignKey("comandas.id"), nullable=False)
    producto_id = Column(String, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(SmallInteger, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    importe = Column(Numeric(10, 2), nullable=False)
    sucursal_id = Column(String, nullable=False)
    notas_especiales = Column(String, nullable=True)
    producto = relationship("Producto")
    comanda = relationship("Comanda", back_populates="detalles")
