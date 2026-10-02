from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "Supplier Invoice Exception Agent"
    environment: str = "development"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./supplier_agent.db"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    chroma_persist_directory: str = "./.chroma"
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    cors_origins: str = "http://localhost:3000"
    max_workflow_retries: int = 2
    upload_max_bytes: int = 10_000_000

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
