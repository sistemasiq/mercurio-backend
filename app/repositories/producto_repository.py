from sqlalchemy.orm import Session
from app.models.producto import Producto

def get_productos_activos(db: Session):
    return db.query(Producto).filter(Producto.activo == True).all()