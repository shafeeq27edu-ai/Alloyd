import pytest
import os
import base64
from cryptography.fernet import Fernet
from pydantic import ValidationError
from app.config import Settings

@pytest.fixture
def clean_env():
    keys = [
        "SECRET_KEY",
        "ENCRYPTION_KEY",
        "DATABASE_URL",
        "DEBUG",
        "COOKIE_SECURE",
        "COOKIE_DOMAIN",
        "ALLOWED_ORIGINS",
        "DB_HOST",
        "DB_PORT",
        "DB_USER",
        "DB_PASSWORD",
        "DB_NAME",
    ]
    saved = {key: os.environ.get(key) for key in keys}
    for key in keys:
        os.environ.pop(key, None)
    yield
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

def test_valid_config(clean_env):
    os.environ["SECRET_KEY"] = "a" * 32
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
    
    settings = Settings(_env_file=None)
    assert settings.SECRET_KEY == "a" * 32
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost/db"

def test_missing_jwt_secret_fails(clean_env):
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
    
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    
    assert "SECRET_KEY" in str(exc.value)

def test_missing_fernet_key_fails(clean_env):
    os.environ["SECRET_KEY"] = "a" * 32
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
    
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    
    assert "ENCRYPTION_KEY" in str(exc.value)

def test_invalid_fernet_key_fails(clean_env):
    os.environ["SECRET_KEY"] = "a" * 32
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
    
    # Not base64
    os.environ["ENCRYPTION_KEY"] = "invalid_fernet_key_that_is_not_base64"
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert "ENCRYPTION_KEY" in str(exc.value)
    
    # Base64 but wrong length
    os.environ["ENCRYPTION_KEY"] = base64.urlsafe_b64encode(b"too_short").decode()
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert "ENCRYPTION_KEY" in str(exc.value)

def test_missing_database_url_fails(clean_env):
    os.environ["SECRET_KEY"] = "a" * 32
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    
    assert "DATABASE_URL" in str(exc.value)

def test_default_or_weak_jwt_secret_fails(clean_env):
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
    
    os.environ["SECRET_KEY"] = "too_short"
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert "SECRET_KEY must be at least 32 characters long" in str(exc.value)
    
    os.environ["SECRET_KEY"] = "super_secret_key_for_testing_only"
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert "cannot be a default or placeholder" in str(exc.value)

def test_no_provider_keys_required(clean_env):
    os.environ["SECRET_KEY"] = "a" * 32
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
    
    # We should not fail if GROQ_API_KEY, GEMINI_API_KEY, etc. are missing.
    settings = Settings(_env_file=None)
    # The config does not even define these, so it passes naturally.
    assert hasattr(settings, "SECRET_KEY")


def test_debug_defaults_off(clean_env):
    os.environ["SECRET_KEY"] = "a" * 32
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"

    settings = Settings(_env_file=None)
    assert settings.DEBUG is False


def test_trusted_proxies_defaults_empty(clean_env):
    os.environ["SECRET_KEY"] = "a" * 32
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"

    settings = Settings(_env_file=None)
    assert settings.TRUSTED_PROXIES == ""


def test_blank_cookie_secure_derives_from_debug(clean_env):
    os.environ["SECRET_KEY"] = "a" * 32
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
    os.environ["COOKIE_SECURE"] = ""

    settings = Settings(_env_file=None)

    assert settings.COOKIE_SECURE is None
    assert settings.cookie_secure is True
    assert settings.cookie_domain is None


def test_cookie_settings_from_env(clean_env):
    os.environ["SECRET_KEY"] = "a" * 32
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
    os.environ["COOKIE_DOMAIN"] = ".example.com"
    os.environ["COOKIE_SECURE"] = "false"

    settings = Settings(_env_file=None)

    assert settings.cookie_domain == ".example.com"
    assert settings.cookie_secure is False


def test_database_url_assembled_from_parts(clean_env):
    os.environ["SECRET_KEY"] = "a" * 32
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    os.environ["DB_HOST"] = "db"
    os.environ["DB_PORT"] = "5432"
    os.environ["DB_USER"] = "alloyd"
    os.environ["DB_PASSWORD"] = "p@ss word"
    os.environ["DB_NAME"] = "alloyd"

    settings = Settings(_env_file=None)

    assert settings.DATABASE_URL == "postgresql+asyncpg://alloyd:p%40ss+word@db:5432/alloyd"


def test_wildcard_origin_is_rejected(clean_env):
    os.environ["SECRET_KEY"] = "a" * 32
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
    os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000,*"

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)

    assert "ALLOWED_ORIGINS" in str(exc.value)
