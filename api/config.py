from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = ""
    db_name: str = "rwanda_emp"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # LLM API (OpenAI)
    openai_api_key: str = ""
    openai_api_url: str = "https://api.openai.com/v1/chat/completions"
    openai_model: str = "gpt-4.1-mini"

    # SkillCraft (psychometric assessment platform)
    skillcraft_api_url: str = "https://api-prod.skillcraft.app"
    skillcraft_pilot_group: str = "dr"

    # Pathways (Strapi e-learning platform)
    pathways_api_url: str = "http://localhost:1337"

    # CORS
    frontend_url: str = "http://localhost:5173"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
