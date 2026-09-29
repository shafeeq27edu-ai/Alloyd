from pydantic_settings import BaseSettings
from pydantic import field_validator
import base64

class Settings(BaseSettings):
    PROJECT_NAME: str = "Alloyd Phase 1"
    DATABASE_URL: str
    SECRET_KEY: str
    ENCRYPTION_KEY: str
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

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long.")
        if v == "super_secret_key_for_testing_only" or v == "replace_with_strong_secret_key":
            raise ValueError("SECRET_KEY cannot be a default or placeholder value.")
        return v

    @field_validator("ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        if v == "VlYp1_8P_aIqTf8w4P5q9G_oV7qHk_4fB_3oU_1Yg_8=" or v == "replace_with_32_byte_url_safe_base64_string=":
            raise ValueError("ENCRYPTION_KEY cannot be a default or placeholder value.")
        try:
            decoded = base64.urlsafe_b64decode(v)
            if len(decoded) != 32:
                raise ValueError("ENCRYPTION_KEY must decode to exactly 32 bytes.")
        except Exception:
            raise ValueError("ENCRYPTION_KEY must be a valid url-safe base64 string.")
        return v

    class Config:
        env_file = ".env"

settings = Settings()

