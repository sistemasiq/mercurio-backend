from uuid import uuid4

from sqlalchemy import text, Boolean, Column, Computed, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class ReservacionExtrasModel(Base):
    """Extras seleccionados para una reservación específica."""

    __tablename__ = "reservacion_extras"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    reservacion_id = Column(PGUUID(as_uuid=True), ForeignKey("reservaciones.id"), nullable=False)
    extra_id = Column(PGUUID(as_uuid=True), ForeignKey("extras.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), Computed("cantidad * precio_unitario", persisted=True))
    creado = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)

    reservacion = relationship("ReservacionModel", back_populates="reservacion_extras")
    extra = relationship("ExtrasModel", back_populates="reservacion_extras")
