from uuid import uuid4

from sqlalchemy import Column, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class ReservacionExtrasModel(Base):
    """Extras seleccionados para una reservación específica."""

    __tablename__ = "reservacion_extras"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    reservacion_id = Column(PGUUID(as_uuid=True), nullable=False)
    extra_id = Column(PGUUID(as_uuid=True), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)  # cantidad * precio_unitario
    creado = Column(String, nullable=False)
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)

    reservacion = relationship("ReservacionModel", back_populates="reservacion_extras")
    extra = relationship("ExtrasModel", back_populates="reservacion_extras")
