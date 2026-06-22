from uuid import uuid4

from sqlalchemy import Column, DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class PagosReservacionModel(Base):
    """Registro de cada pago realizado contra una reservación."""

    __tablename__ = "pagos_reservacion"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    reservacion_id = Column(PGUUID(as_uuid=True), nullable=False)
    metodo_pago_id = Column(PGUUID(as_uuid=True), nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    fecha_pago = Column(DateTime, nullable=False)
    notas = Column(String(255), nullable=True)
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)

    reservacion = relationship("ReservacionModel", back_populates="pagos")
    metodo_pago = relationship("MetodosPagoModel", back_populates="pagos")
