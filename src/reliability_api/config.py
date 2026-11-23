from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RELIABILITY_", extra="ignore")
    database_url: str = "sqlite:///./reliability_tri.db"
    api_key: str | None = None
    max_sync_rules: int = 200
    service_name: str = "Reliability TRI API"
    service_version: str = "0.2.0"

settings = Settings()
