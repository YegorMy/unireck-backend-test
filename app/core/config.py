"""Application settings via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="API_")

    project_name: str = "api"
    database_url: str = ""
    database_echo: bool = False
    llm_provider: str = "fake"
    fake_provider_mode: str = "valid"
    api_key: str = ""
    cors_allow_origin_regex: str = r"chrome-extension://.*"
    cors_allow_methods: list[str] = ["GET", "POST", "OPTIONS"]
    cors_allow_headers: list[str] = ["Content-Type", "X-API-Key"]
    cors_allow_credentials: bool = False


settings = Settings()
