from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://lifeos:lifeos@127.0.0.1:5432/lifeos"
    redis_url: str | None = "redis://127.0.0.1:6379/0"
    lifeos_data_root: Path = Path(__file__).resolve().parents[1] / "data"
    lifeos_api_key: str = "dev-lifeos-key-change-me"
    lifeos_host: str = "0.0.0.0"
    lifeos_port: int = 8000
    context_cache_ttl_seconds: int = 30
    lifeos_intent_classifier: str = "rules"
    lifeos_intent_timeout_seconds: float = 3.0
    deepseek_api_key: str | None = None
    deepseek_dream_model: str = "deepseek-v4-pro"
    deepseek_dream_base_url: str = "https://api.deepseek.com"
    deepseek_intent_model: str = "deepseek-chat"
    deepseek_intent_base_url: str | None = None

    @property
    def worlds_data_root(self) -> Path:
        return self.lifeos_data_root / "worlds"

    @property
    def intent_base_url(self) -> str:
        return self.deepseek_intent_base_url or self.deepseek_dream_base_url


settings = Settings()
