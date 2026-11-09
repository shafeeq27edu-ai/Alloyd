from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
import base64
from urllib.parse import quote_plus

class Settings(BaseSettings):
    PROJECT_NAME: str = "Alloyd Phase 1"
    DATABASE_URL: str | None = None
    # Alternative to DATABASE_URL, used by container platforms that inject
    # database parts instead of a single URL.
    DB_HOST: str | None = None
    DB_PORT: int = 5432
    DB_USER: str | None = None
    DB_PASSWORD: str | None = None
    DB_NAME: str = "alloyd"
    SECRET_KEY: str
    ENCRYPTION_KEY: str
    PREVIOUS_ENCRYPTION_KEY: str | None = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    # Comma-separated IPs/CIDRs whose X-Forwarded-For header is trusted.
    TRUSTED_PROXIES: str = ""
    MAX_REQUEST_BYTES: int = 1_000_000

    # Cookie scoping. COOKIE_DOMAIN is required for sibling subdomains
    # (e.g. ".alloyd.com" so app.alloyd.com and api.alloyd.com share the
    # auth cookie). COOKIE_SECURE defaults to the inverse of DEBUG.
    COOKIE_DOMAIN: str | None = None
    COOKIE_SECURE: bool | None = None

    # Logging.
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Database readiness / pooler behavior.
    DB_CONNECT_TIMEOUT_SECONDS: float = 5.0
    DB_DISABLE_PREPARED_STATEMENTS: bool = False
    STARTUP_DB_CHECK_RETRIES: int = 10
    STARTUP_DB_CHECK_DELAY_SECONDS: float = 2.0

    # Rate Limiting Settings
    LOGIN_RATE_LIMIT: int = 5
    LOGIN_RATE_WINDOW: int = 60
    REGISTRATION_RATE_LIMIT: int = 3
    REGISTRATION_RATE_WINDOW: int = 3600
    CHAT_RATE_LIMIT: int = 15
    CHAT_RATE_WINDOW: int = 60

    # Provider request limits (seconds)
    PROVIDER_TIMEOUT_SECONDS: float = 60.0
    PROVIDER_FIRST_CHUNK_TIMEOUT_SECONDS: float = 20.0

    @model_validator(mode="after")
    def assemble_database_url(self):
        if self.DATABASE_URL:
            return self
        if self.DB_HOST and self.DB_USER is not None and self.DB_PASSWORD is not None:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
            return self
        raise ValueError(
            "DATABASE_URL must be set (or provide DB_HOST, DB_USER, DB_PASSWORD, and DB_NAME)."
        )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @field_validator("COOKIE_SECURE", mode="before")
    @classmethod
    def blank_cookie_secure(cls, v):
        # `.env.example` ships an empty value meaning "derive from DEBUG".
        if v == "":
            return None
        return v

    @property
    def cookie_secure(self) -> bool:
        return self.COOKIE_SECURE if self.COOKIE_SECURE is not None else not self.DEBUG

    @property
    def cookie_domain(self) -> str | None:
        return self.COOKIE_DOMAIN or None

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def validate_allowed_origins(cls, v: str) -> str:
        origins = [origin.strip() for origin in v.split(",") if origin.strip()]
        if "*" in origins:
            raise ValueError("ALLOWED_ORIGINS cannot contain a wildcard when credentials are enabled.")
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long.")
        if v == "super_secret_key_for_testing_only" or v == "replace_with_strong_secret_key":
            raise ValueError("SECRET_KEY cannot be a default or placeholder value.")
        return v

    @field_validator("ENCRYPTION_KEY", "PREVIOUS_ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, v: str | None) -> str | None:
        if v is None:
            return v
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

