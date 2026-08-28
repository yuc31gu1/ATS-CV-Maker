from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ats-cv-backend"
    database_url: str = "postgresql+psycopg://ats:ats@localhost:5432/ats"
    llm_provider: str = "fixture"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ATS_")


settings = Settings()