from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Alloyd Phase 1"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:54322/postgres" # Default to local pg/supabase if not set
    SECRET_KEY: str = "super_secret_key_for_testing_only" # In production, use a strong key
    ENCRYPTION_KEY: str = "VlYp1_8P_aIqTf8w4P5q9G_oV7qHk_4fB_3oU_1Yg_8=" # For Fernet
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    DEBUG: bool = True
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Rate Limiting Settings
    LOGIN_RATE_LIMIT: int = 5
    LOGIN_RATE_WINDOW: int = 60
    REGISTRATION_RATE_LIMIT: int = 3
    REGISTRATION_RATE_WINDOW: int = 3600
    CHAT_RATE_LIMIT: int = 15
    CHAT_RATE_WINDOW: int = 60

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"

settings = Settings()
