from uuid import uuid4
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.database import Base

class ReservacionExtrasModel(Base):
    __tablename__ = "reservacion_extras"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    reservacion_id = Column(PG_UUID(as_uuid=True), ForeignKey("reservaciones.id"), nullable=False)
    extra_id = Column(PG_UUID(as_uuid=True), ForeignKey("extras.id"), nullable=False)
    cantidad = Column(Float, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    sub_total = Column(Float, nullable=False)
    creado = Column(DateTime, default=datetime.utcnow)
    creado_por = Column(String(255), nullable=False)

    reservacion = relationship("Reservacion", back_populates="reservacion_extras")
    extra = relationship("Extras", back_populates="reservacion_extras")