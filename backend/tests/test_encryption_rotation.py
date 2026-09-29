import pytest
import base64
from cryptography.fernet import Fernet
from app.core import encryption
from app.config import settings

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
