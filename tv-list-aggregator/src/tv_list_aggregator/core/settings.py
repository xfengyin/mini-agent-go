"""应用全局配置（pydantic-settings）。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从环境变量或 .env 加载配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///:memory:"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_min: int = 60

    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20240620"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    enable_telemetry: bool = False
    otlp_endpoint: str = ""

    rate_limit_per_minute: int = 120
    plugin_dir: str = "./plugins"
    legal_notice_file: str = "./config/legal_notice.md"

    health_check_fail_threshold: int = 3


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取缓存的全局 Settings 实例。"""
    return Settings()
