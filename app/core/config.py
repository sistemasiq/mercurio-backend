from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql://usuario:password@localhost:5432/mercurio"
    SECRET_KEY: str = "dev-secret-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    CORS_ORIGINS: str = "http://localhost:5173"
    APP_TITLE: str = "Mercurio API"
    APP_VERSION: str = "0.1.0"

    @property
    def asyncpg_dsn(self) -> str:
        """DSN limpio para asyncpg (sin el dialecto SQLAlchemy ``+asyncpg``)."""
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace(
            "postgres+asyncpg://", "postgresql://"
        )


settings = Settings()
