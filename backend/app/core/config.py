from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "K12-UserProfile"
    api_prefix: str = "/api/v1"
    debug: bool = True

    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/profile_rec"
    )

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 86400
    wecom_token_expire_seconds: int = 7200

    llm_provider: str = "deepseek"
    deepseek_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"

    mock_wecom: bool = True
    mock_llm: bool = True

    wecom_corp_id: str = ""
    wecom_secret: str = ""

    # Seed admin (created on first seed)
    seed_admin_login: str = "admin"
    seed_admin_password: str = "admin123"


@lru_cache
def get_settings() -> Settings:
    return Settings()
