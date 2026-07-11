import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.database import Base

class PagosReservacionModel(Base):
    __tablename__ = "pagos_reservacion"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    reservacion_id = Column(PG_UUID(as_uuid=True), ForeignKey("reservaciones.id"), nullable=False)
    metodo_pago_id = Column(PG_UUID(as_uuid=True), ForeignKey("metodos_pago.id"), nullable=False)
    monto = Column(Float, nullable=False)
    fecha_pago = Column(DateTime, default=datetime.datetime.utcnow)
    notas = Column(String(500), nullable=False)
    creado_por = Column(String(255), nullable=False)

    reservacion = relationship("Reservacion", back_populates="pagos_reservacion")
    metodo_pago = relationship("MetodosPago", back_populates="reservacion_metodos_pago")