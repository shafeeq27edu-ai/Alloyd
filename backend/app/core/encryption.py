from cryptography.fernet import Fernet
from app.config import settings

# Initialize fernet with the master encryption key from settings
# Settings validation ensures this key is exactly 32 url-safe base64-encoded bytes
try:
    _cipher_suite = Fernet(settings.ENCRYPTION_KEY.encode('utf-8'))
except Exception as e:
    raise RuntimeError(f"Invalid ENCRYPTION_KEY: {e}")

def encrypt_key(plain_text: str) -> str:
    """Encrypts a plaintext string and returns the ciphertext as a string."""
    return _cipher_suite.encrypt(plain_text.encode('utf-8')).decode('utf-8')

def decrypt_key(cipher_text: str) -> str:
    """Decrypts a ciphertext string and returns the plaintext as a string."""
    return _cipher_suite.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
