from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.dependencies import get_current_user
from app.schemas.sucursal import SucursalBase, SucursalUpdate, SucursalResponse
from app.services import SucursalService as svc

router = APIRouter(prefix="/sucursales", tags=["Sucursales"])

router.get("/", response_model=list[SucursalResponse])
async def listar_sucursales(db: AsyncSession = Depends(get_session), _: str = Depends(get_current_user)):
    rows = await svc.listar_sucursales(db)
    return rows

router.post("/", response_model=SucursalResponse)
async def crear_sucursal(sucursal: SucursalBase, db: AsyncSession = Depends(get_session), _: str = Depends(get_current_user)):
    row = await svc.crear_sucursal(db, sucursal)
    return row

router.patch("/", response_model=SucursalResponse)
async def 

router.put("/{sucursal_id}", response_model=SucursalResponse)
async def actualizar_sucursal(sucursal_id: str, sucursal: SucursalUpdate, db: AsyncSession = Depends(get_session), _: str = Depends(get_current_user)):
    row = await svc.actualizar_sucursal(db, sucursal_id, sucursal)
    return row

router.delete("/{sucursal_id}")
async def eliminar_sucursal(sucursal_id: str, db: AsyncSession = Depends(get_session), _: str = Depends(get_current_user)):
    await svc.eliminar_sucursal(db, sucursal_id)
    return {"detail": "Sucursal eliminada exitosamente."}