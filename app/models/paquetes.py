from uuid import uuid4
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.database import Base

class PaqquetesBase(Base):
    __tablename__ = "paquetes"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    sucursal_id = Column(PG_UUID(as_uuid=True), ForeignKey("sucursales.id"), nullable=False)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(String(500), nullable=True)
    duracion_minutos = Column(Float, nullable=False)
    personas_incluidas = Column(Float, nullable=False)
    precio_base = Column(Float, nullable=False)
    precio_persona_extra = Column(Float, nullable=False)
    activo = Column(Boolean, default=True)
    creado = Column(DateTime, default=datetime.utcnow)
    creado_por = Column(String(255), nullable=False)
    modificado = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    modificado_por = Column(String(255), nullable=False)

    sucursal = relationship("Sucursal", back_populates="paquetes")
    paquete_tipos_evento = relationship("PaqueteTiposEvento", back_populates="paquete")