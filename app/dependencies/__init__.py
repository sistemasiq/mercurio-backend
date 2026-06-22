from sqlalchemy.testing.pickleable import User

from fastapi import Depends, Header
from jose import JWTError, jwt
from app.core.config import settings
from app.exceptions import CredencialesInvalidas

def get_current_user(authorization: str = Header(...)) -> str:
    try:
        token = authorization.removeprefix("Bearer")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload["sub"]
    except JWTError:
        raise CredencialesInvalidas()
