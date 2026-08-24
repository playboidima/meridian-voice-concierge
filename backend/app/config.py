from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://meridian:change-me@db:5432/meridian"
    faq_match_threshold: float = 0.35
    semantic_match_threshold: float = 0.65
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
