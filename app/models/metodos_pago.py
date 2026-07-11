from uuid import uuid4
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.database import Base

class MetodosPagoModel(Base):
    __tablename__ = "metodos_pago"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    sucursal_id = Column(PG_UUID(as_uuid=True), ForeignKey("sucursales.id"), nullable=False)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(String(500), nullable=True)
    activo = Column(Boolean, default=True)
    creado = Column(DateTime, default=datetime.utcnow)
    creado_por = Column(String(255), nullable=False)
    modificado = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    modificado_por = Column(String(255), nullable=False)

    sucursal = relationship("Sucursal", back_populates="metodos_pago")
    reservacion_metodos_pago = relationship("ReservacionMetodosPago", back_populates="metodo_pago")
