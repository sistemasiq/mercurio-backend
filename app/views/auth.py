from pydantic import BaseModel


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
