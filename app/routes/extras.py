from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_session
from app.dependencies import get_current_user

from app.schemas.extras import ExtrasOut
import app.services.extras as sExtras

router = APIRouter(prefix="/extras", tags=["Extras"])
