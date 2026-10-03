from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_role
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.padres import (
    PadreAuthRequest,
    PadreDashboardResponse,
    PadreNinosActivosResponse,
)
from app.services.padres_service import (
    TokenAccesoInvalidoError,
    get_ninos_activos,
    get_padre_dashboard,
)

router = APIRouter(prefix="/api/padres", tags=["Padres"])

_TOKEN_INVALIDO = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail={
        "code": "TOKEN_INVALIDO",
        "message": "El código de acceso no es válido o está mal formado.",
    },
)
_SESION_INVALIDA = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={
        "code": "SESION_INVALIDA",
        "message": "La sesión ya no es válida. Vuelve a escanear el código.",
    },
)


@router.post("/auth", response_model=PadreDashboardResponse)
async def auth_padre(
    body: PadreAuthRequest,
    conn: asyncpg.Connection = Depends(get_db),
) -> PadreDashboardResponse:
    try:
        return await get_padre_dashboard(conn, body.code)
    except TokenAccesoInvalidoError:
        raise _TOKEN_INVALIDO from None


@router.get("/ninos-activos", response_model=PadreNinosActivosResponse)
async def ninos_activos_endpoint(
    current_user: TokenData = Depends(require_role("PadreVisor")),
    conn: asyncpg.Connection = Depends(get_db),
) -> PadreNinosActivosResponse:
    """QA #31 — polling del dashboard con el token de `/padres/auth`
    (Authorization: Bearer), sin volver a mandar el código cada vez. Un 401 o
    403 (token revocado/expirado o registro ya no activo) debe cerrar la
    sesión en el front."""
    try:
        registro_id = UUID(current_user.sub)
    except ValueError:
        raise _SESION_INVALIDA from None

    try:
        return await get_ninos_activos(conn, registro_id)
    except TokenAccesoInvalidoError:
        raise _SESION_INVALIDA from None
