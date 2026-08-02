from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    access_token_remember_me_minutes: int = 60 * 24 * 7  # 7 días
    refresh_token_expire_days: int = 7
    refresh_token_remember_me_days: int = 30

    database_url: str

    cors_origins: list[str] = ["http://localhost:5173"]

    minio_endpoint: str = "minio:9000"
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "mercury"
    minio_secure: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
