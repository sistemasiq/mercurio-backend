from sqlalchemy.orm import Session
from app.models.comanda import Comanda, DetalleComanda
from app.core.utils import get_mexico_now
import uuid
from app.schemas import comanda as schemas
from sqlalchemy.orm import joinedload


def crear_comanda_con_detalles(db: Session, comanda_in):
    try:
        # Ya no necesitas comanda_data['campo'], usa comanda_in.campo
        comanda_id = str(uuid.uuid4())
        nueva_comanda = Comanda(
            id=comanda_id,
            ticket_numero=comanda_in.ticket_numero,
            total_final=comanda_in.total_final,
            sucursal_id=comanda_in.sucursal_id,
            estado_actual=comanda_in.estado_actual.value,
            fecha_hora=get_mexico_now()
        )
        db.add(nueva_comanda)

        # Iteras sobre comanda_in.detalles_comanda directamente
        for item in comanda_in.detalles_comanda:
            detalle = DetalleComanda(
                id=str(uuid.uuid4()),
                comanda_id=comanda_id,
                producto_id=item.id,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                importe=item.subtotal,
                sucursal_id=comanda_in.sucursal_id,
                notas_especiales=getattr(item, 'notas_especiales', None)
            )
            db.add(detalle)

        db.commit()
        db.refresh(nueva_comanda)
        return nueva_comanda
        
    except Exception as e:
        db.rollback()
        raise e
    
def actualizar_estado_comanda(db: Session, comanda_id: str, nuevo_estado: str):
    comanda = db.query(Comanda).filter(Comanda.id == comanda_id).first()
    if not comanda:
        return None
    
    comanda.estado_actual = nuevo_estado
    # Opcional: registrar quién y cuándo lo modificó
    # comanda.modificado = get_mexico_now()
    
    db.commit()
    db.refresh(comanda)
    return comanda

def get_comandas_pendientes(db: Session):
    return db.query(Comanda)\
        .options(
            joinedload(Comanda.detalles)
            .joinedload(DetalleComanda.producto) # Asegúrate de tener esta relación
        )\
        .filter(Comanda.estado_actual.in_(['P', 'E']))\
        .all()