from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    rememberMe: bool = False


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    roles: list[str]


class LoginResponse(BaseModel):
    token: str
    expiresIn: int
    user: UserOut
