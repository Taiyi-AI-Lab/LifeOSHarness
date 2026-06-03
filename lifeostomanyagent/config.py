from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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
    bws_fuxian_root: Path = repo_root() / "003-life-os"

    @property
    def worlds_data_root(self) -> Path:
        return self.lifeos_data_root / "worlds"


settings = Settings()
