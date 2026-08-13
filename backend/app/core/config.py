"""应用配置：从环境变量 / .env 加载运行参数。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置项；字段名即环境变量名（大小写不敏感）。"""

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

    # LLM：mock_llm=True 时走 Fake 提供商，忽略真实 Key
    llm_provider: str = "deepseek"
    deepseek_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"

    mock_wecom: bool = True
    mock_llm: bool = True

    asr_provider: str = "fake"
    asr_api_key: str = ""

    wecom_corp_id: str = ""
    wecom_secret: str = ""

    # 首次 seed 时创建的后台管理员账号
    seed_admin_login: str = "admin"
    seed_admin_password: str = "admin123"


@lru_cache
def get_settings() -> Settings:
    """进程内单例配置；修改 .env 后需重启进程才会生效。"""
    return Settings()
