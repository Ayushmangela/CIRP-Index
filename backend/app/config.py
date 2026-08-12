from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = (
        "postgresql://postgres:postgrespassword@localhost:5432/cirp_index"
    )
    TEST_DATABASE_URL: str = (
        "postgresql://postgres:postgrespassword@localhost:5432/cirp_index_test"
    )
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    GEMINI_API_KEY: str = ""
    IBBI_CONTACT_EMAIL: str = "info@cirpindex.org"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
