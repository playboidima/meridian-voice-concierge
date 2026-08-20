from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://meridian:change-me@db:5432/meridian"
    faq_match_threshold: float = 0.35

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
