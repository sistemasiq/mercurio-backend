from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from jose import jwt

from app.config import settings
from app.views.auth import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])

# usuarios de prueba — reemplazar con consulta a DB
USERS = {
    "oscarmajai": {
        "id": 1,
        "name": "Oscar Magana Jaime",
        "email": "admin@oscarmajai.dev",
        "password": "123456",
        "roles": ["admin"],
    }
}


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    user = USERS.get(body.email.lower())

    if not user or user["password"] != body.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Credenciales incorrectas."},
        )

    expires_minutes = 60 * 24 if body.rememberMe else 60
    exp = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)

    token = jwt.encode(
        {"sub": user["email"], "exp": exp},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    return LoginResponse(
        token=token,
        expiresIn=expires_minutes * 60,
        user=UserOut(**{k: user[k] for k in ("id", "name", "email", "roles")}),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout():
    pass
