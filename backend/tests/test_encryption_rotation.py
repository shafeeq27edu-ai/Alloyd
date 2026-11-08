import pytest
import base64
import importlib.util
from pathlib import Path
from cryptography.fernet import Fernet, MultiFernet
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core import encryption
from app.config import settings
from app.db.database import Base
from app.db.models import ProviderKey, User

def test_encryption_decryption_single_key(monkeypatch):
    # Ensure only active key is set
    active_key = Fernet.generate_key()
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", active_key.decode('utf-8'))
    monkeypatch.setattr(settings, "PREVIOUS_ENCRYPTION_KEY", None)
    
    # Reload encryption module to pick up monkeypatched settings
    import importlib
    importlib.reload(encryption)
    
    plaintext = "super_secret_api_key"
    ciphertext = encryption.encrypt_key(plaintext)
    
    assert ciphertext != plaintext
    assert encryption.decrypt_key(ciphertext) == plaintext

def test_decryption_old_ciphertext(monkeypatch):
    old_key = Fernet.generate_key()
    new_key = Fernet.generate_key()
    
    # Encrypt with old key directly
    old_fernet = Fernet(old_key)
    old_ciphertext = old_fernet.encrypt(b"my_old_secret").decode('utf-8')
    
    # Setup dual keys
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", new_key.decode('utf-8'))
    monkeypatch.setattr(settings, "PREVIOUS_ENCRYPTION_KEY", old_key.decode('utf-8'))
    
    import importlib
    importlib.reload(encryption)
    
    # Should successfully decrypt
    assert encryption.decrypt_key(old_ciphertext) == "my_old_secret"

def test_new_encryption_uses_active_key(monkeypatch):
    old_key = Fernet.generate_key()
    new_key = Fernet.generate_key()
    
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", new_key.decode('utf-8'))
    monkeypatch.setattr(settings, "PREVIOUS_ENCRYPTION_KEY", old_key.decode('utf-8'))
    
    import importlib
    importlib.reload(encryption)
    
    plaintext = "brand_new_secret"
    ciphertext = encryption.encrypt_key(plaintext)
    
    # Should decrypt successfully with dual setup
    assert encryption.decrypt_key(ciphertext) == plaintext
    
    # Let's verify it was actually encrypted with the NEW key, not the old key
    new_fernet = Fernet(new_key)
    assert new_fernet.decrypt(ciphertext.encode('utf-8')).decode('utf-8') == plaintext
    
    # Old key alone should fail to decrypt it
    old_fernet = Fernet(old_key)
    with pytest.raises(Exception):
        old_fernet.decrypt(ciphertext.encode('utf-8'))

def test_config_validation_previous_key():
    from pydantic import ValidationError
    from app.config import Settings
    
    # Valid setup
    valid_key = Fernet.generate_key().decode('utf-8')
    s = Settings(
        DATABASE_URL="sqlite:///./test.db",
        SECRET_KEY="super_secret_key_for_production_only_123456",
        ENCRYPTION_KEY=valid_key,
        PREVIOUS_ENCRYPTION_KEY=valid_key
    )
    assert s.PREVIOUS_ENCRYPTION_KEY == valid_key
    
    # Invalid previous key
    with pytest.raises(ValidationError):
        Settings(
            DATABASE_URL="sqlite:///./test.db",
            SECRET_KEY="super_secret_key_for_production_only_123456",
            ENCRYPTION_KEY=valid_key,
            PREVIOUS_ENCRYPTION_KEY="invalid_base64_string"
        )


@pytest.mark.asyncio
async def test_rotate_keys_reencrypts_rows_with_active_key(tmp_path, monkeypatch, capsys):
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "rotate_keys.py"
    spec = importlib.util.spec_from_file_location("rotate_keys_script", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'rotation.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    old_key = Fernet.generate_key()
    new_key = Fernet.generate_key()
    original_ciphertext = Fernet(old_key).encrypt(b"provider-secret").decode()

    async with session_factory() as session:
        user = User(email="rotate@example.com", hashed_password="unused")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        row = ProviderKey(
            user_id=user.id,
            provider_name="groq",
            encrypted_key=original_ciphertext,
            key_hint="cret"
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        row_id = row.id

    monkeypatch.setattr(module.settings, "PREVIOUS_ENCRYPTION_KEY", old_key.decode())
    monkeypatch.setattr(module, "_cipher_suite", MultiFernet([Fernet(new_key), Fernet(old_key)]))
    monkeypatch.setattr(module, "AsyncSessionLocal", session_factory)

    await module.rotate_keys(dry_run=False)

    async with session_factory() as session:
        rotated = await session.get(ProviderKey, row_id)
        assert rotated.encrypted_key != original_ciphertext
        assert Fernet(new_key).decrypt(rotated.encrypted_key.encode()).decode() == "provider-secret"
        with pytest.raises(Exception):
            Fernet(old_key).decrypt(rotated.encrypted_key.encode())

    output = capsys.readouterr().out
    assert "Rotated: 1" in output
    assert "provider-secret" not in output

    await engine.dispose()

