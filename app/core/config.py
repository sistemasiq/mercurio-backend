# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List 

class Settings(BaseSettings):
    database_url: str
    app_name: str = "Mercurio Backend"
    debug: bool = False
    cors_origins: List[str] = [] 

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()