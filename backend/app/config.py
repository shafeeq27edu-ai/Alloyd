from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Alloyd Phase 1"
    DATABASE_URL: str = "sqlite+aiosqlite:///./alloyd.db"
    SECRET_KEY: str = "super_secret_key_for_testing_only" # In production, use a strong key
    ENCRYPTION_KEY: str = "VlYp1_8P_aIqTf8w4P5q9G_oV7qHk_4fB_3oU_1Yg_8=" # For Fernet
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    class Config:
        env_file = ".env"

settings = Settings()
