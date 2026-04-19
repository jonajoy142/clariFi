from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str = ""
    model: str = "claude-sonnet-4-20250514"
    debug: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
