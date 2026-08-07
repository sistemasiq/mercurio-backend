import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_db
from app.schemas.padres import PadreAuthRequest, PadreDashboardResponse
from app.services.padres_service import TokenAccesoInvalido, get_padre_dashboard

router = APIRouter(prefix="/api/padres", tags=["Padres"])


@router.post("/auth", response_model=PadreDashboardResponse)
async def auth_padre(
    body: PadreAuthRequest,
    conn: asyncpg.Connection = Depends(get_db),
) -> PadreDashboardResponse:
    try:
        return await get_padre_dashboard(conn, body.code)
    except TokenAccesoInvalido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TOKEN_INVALIDO",
                "message": "El código de acceso no es válido o está mal formado.",
            },
        )
