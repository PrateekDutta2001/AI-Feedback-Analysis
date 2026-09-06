"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings for InsightAI."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "InsightAI"
    app_env: str = "development"
    debug: bool = True

    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = "sqlite:///./insightai.db"

    model_dir: str = "./models"
    data_dir: str = "./data"
    log_dir: str = "./logs"
    export_dir: str = "./exports"

    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    similarity_threshold: float = 0.85
    max_upload_mb: int = 15
    default_user: str = "analyst"

    dashboard_cache_seconds: int = 45

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def model_path(self) -> Path:
        path = Path(self.model_dir)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def data_path(self) -> Path:
        path = Path(self.data_dir)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def log_path(self) -> Path:
        path = Path(self.log_dir)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def export_path(self) -> Path:
        path = Path(self.export_dir)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def sqlite_file(self) -> Path:
        if self.database_url.startswith("sqlite:///"):
            raw = self.database_url.replace("sqlite:///", "", 1)
            path = Path(raw)
            return path if path.is_absolute() else PROJECT_ROOT / path
        return PROJECT_ROOT / "insightai.db"

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url.startswith("sqlite:///"):
            return f"sqlite:///{self.sqlite_file.as_posix()}"
        return self.database_url

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    settings = Settings()
    for directory in (
        settings.model_path,
        settings.data_path,
        settings.log_path,
        settings.export_path,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return settings
