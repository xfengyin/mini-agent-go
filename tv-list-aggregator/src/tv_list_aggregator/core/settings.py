"""应用全局配置（pydantic-settings）。"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从环境变量或 .env 加载配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
        env_prefix="TV_LIST_",  # 匹配 TV_LIST_DATABASE_URL / TV_LIST_SECRET_KEY 等
    )

    # ---- 应用 ----
    app_env: str = "development"  # development | staging | production
    log_level: str = "INFO"

    # ---- 持久化 ----
    database_url: str = "sqlite+aiosqlite:///:memory:"
    redis_url: str = "redis://localhost:6379/0"

    # ---- 安全（强制无默认值；非 dev 环境启动期强校验） ----
    # 见 lifespan / get_settings 二次校验
    secret_key: SecretStr = Field(default=SecretStr("change-me"))
    jwt_algorithm: str = "HS256"
    access_token_ttl_min: int = 60

    # ---- LLM ----
    llm_provider: str = "openai"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: SecretStr = SecretStr("")
    anthropic_model: str = "claude-3-5-sonnet-20240620"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # ---- 可观测 ----
    enable_telemetry: bool = False
    otlp_endpoint: str = ""

    # ---- 弹性 ----
    rate_limit_per_minute: int = 120

    # ---- 插件 ----
    plugin_dir: str = "./plugins"
    legal_notice_file: str = "./config/legal_notice.md"

    # ---- 健康检查 ----
    health_check_fail_threshold: int = 3

    # ---- 启动种子（dev 友好） ----
    # 格式：admin1:bcrypt_hash1,admin2:bcrypt_hash2
    # 通过 CLI 工具 `python -m tv_list_aggregator.tools.hash_password` 生成 hash
    seed_users: str = ""

    def is_production(self) -> bool:
        """判断是否生产环境。"""
        return self.app_env.lower() in {"production", "prod", "staging"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取缓存的全局 Settings 实例。

    非 dev 环境下 secret_key 仍为占位符 'change-me' 时直接抛错，
    防止 JWT 签名密钥以默认值上生产。
    """
    s = Settings()
    if s.is_production() and s.secret_key.get_secret_value() == "change-me":
        raise RuntimeError(
            "TV_LIST_SECRET_KEY is required in non-dev environment; "
            "refusing to start with the default placeholder."
        )
    return s


def reset_settings_cache() -> None:
    """仅供测试使用：清空 lru_cache。"""
    get_settings.cache_clear()
