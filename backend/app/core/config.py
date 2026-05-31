from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "clariFi CFO OS"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://clarifi:clarifi@localhost:5432/clarifi"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    litellm_model: str = "anthropic/claude-3-5-sonnet-20241022"
    model: str = "claude-sonnet-4-20250514"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    enable_pgvector: bool = False
    seed_on_startup: bool = False
    debug: bool = False

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
