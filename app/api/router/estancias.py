from typing import List
from uuid import UUID
from app.core.database import get_db
import asyncpg
from starlette import status

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from pydantic import ValidationError
from app.schemas.registros import DetalleActivoResponse, OnboardingResponse,OnboardingRequest,CheckoutResponse,ProductoResponse
from app.schemas.pagos import PagoIn

from app.services.estancias import get_activos_estancia_by_sucursal_id,get_productos_estancia_by_id_sucursal
from app.services.pagos_estancia import pago_create_service
from app.services.chekouts import create_chekout


router = APIRouter(prefix="/api/estancias", tags=["Estancias"])


@router.get(
   "/activos/{sucursal_id}",
   response_model=List[DetalleActivoResponse],
   summary="Listar niños en estancia",
   description="Consulta todos los niños que se encuentran activos actualmente en la sucursal."
)
async def get_activos(
   sucursal_id: UUID,
   conn: asyncpg.Connection = Depends(get_db)
):

   return get_activos_estancia_by_sucursal_id(conn,sucursal_id)




@router.post(
   "/",
   status_code=status.HTTP_201_CREATED,
   response_model=OnboardingResponse,
   summary="Registrar entrada de niños",
   description="Crea un registro de entrada completo vinculando al tutor, los niños y procesando el pago inicial."
)
async def onboarding(
   fotoIne: UploadFile = File(...),
   fotoLlegada: UploadFile = File(...),
   payload: str = Form(..., description="JSON string con los datos de OnboardingRequest"),
   conn: asyncpg.Connection = Depends(get_db)
):
   try:
       data = OnboardingRequest.model_validate_json(payload)
   except ValidationError as e:
       raise HTTPException(status_code=422, detail=e.errors())


   service = OnboardingRequest()
   usuario_id = UUID("11111111-1111-1111-1111-111111111111")


   return await service.execute(conn, data, fotoIne, fotoLlegada, usuario_id)


@router.post(
   "/{registro_id}/pagos",
   status_code=status.HTTP_201_CREATED,
   summary="Registrar pago adicional",
   description="Registra uno o más pagos extraordinarios vinculados a un registro de estancia existente."
)
async def pago_estancia_extra(
   registro_id:UUID,
   pagos:List[PagoIn],
   sucursal_id:UUID,
   conn: asyncpg.Connection = Depends(get_db)
):
   usuario_id = UUID("11111111-1111-1111-1111-111111111111")
   return await pago_create_service(conn,pagos,sucursal_id,registro_id,usuario_id)


      


#Endpoint para calcular checkout
@router.post(
   "/checkout/{detalle_id}",
   status_code=status.HTTP_201_CREATED,
   response_model=CheckoutResponse,
   summary="Procesar salida del niño",
   description="Registra la salida, calcula cargos extra por tiempo y marca el registro como finalizado si corresponde."
)
async def checkout(
   detalle_id: UUID,
   conn: asyncpg.Connection = Depends(get_db)
):
   usuario_id = "11111111-1111-1111-1111-111111111111"


   return await create_chekout(conn, detalle_id, usuario_id)


@router.get(
   "/productos/{sucursal_id}",
   response_model=List[ProductoResponse],
   summary="Listar productos",
   description="Obtiene el catálogo de productos tipo 'estancia' activos para la sucursal."
)
async def get_productos(
   sucursal_id: UUID,
   conn: asyncpg.Connection = Depends(get_db)
):


   return get_productos_estancia_by_id_sucursal(conn,sucursal_id)


