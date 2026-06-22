from uuid import uuid4

from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class MetodosPagoModel(Base):
    """Catálogo de métodos de pago aceptados (efectivo, tarjeta, etc.)."""

    __tablename__ = "metodos_pago"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    creado = Column(String, nullable=False)
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)
    modificado = Column(String, nullable=True)
    modificado_por = Column(PGUUID(as_uuid=True), nullable=True)

    pagos = relationship("PagosReservacionModel", back_populates="metodo_pago")
