import pytest
import os
import base64
from cryptography.fernet import Fernet
from pydantic import ValidationError
from app.config import Settings

@pytest.fixture
def clean_env():
    # Remove relevant env vars to start fresh
    for key in ["SECRET_KEY", "ENCRYPTION_KEY", "DATABASE_URL"]:
        if key in os.environ:
            del os.environ[key]

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
