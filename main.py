from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import jwt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"

app = FastAPI(title="TEC-FS Auth API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# ── Usuarios de prueba ──────────────────────────────────────
USERS = {
    "oscarmajai": {
        "id": 1,
        "name": "Oscar Magana Jaime",
        "email": "admin@oscarmajai.dev",
        "password": "123456",
        "roles": ["admin"],
    }
}

# ── Modelos ─────────────────────────────────────────────────
class LoginRequest(BaseModel):
    branchId: str
    email: str
    password: str
    rememberMe: bool = False

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    roles: list[str]

class LoginResponse(BaseModel):
    token: str
    tokenType: str = "Bearer"
    expiresIn: int
    user: UserOut

# ── Endpoints ───────────────────────────────────────────────
@app.post("/api/auth/login", response_model=LoginResponse)
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
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return LoginResponse(
        token=token,
        expiresIn=expires_minutes * 60,
        user=UserOut(**{k: user[k] for k in ("id", "name", "email", "roles")}),
    )

@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout():
    pass
