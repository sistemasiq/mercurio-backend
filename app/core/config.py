from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+asyncpg://usuario:password@localhost:5432/mercurio"
    SECRET_KEY: str = "dev-secret-change-in-production"
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: str = "http://localhost:5173"
    APP_TITLE: str = "Mercurio API"
    APP_VERSION: str = "0.1.0"


settings = Settings()
