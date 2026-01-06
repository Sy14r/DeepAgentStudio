from cryptography.fernet import Fernet
from typing import Optional
from ..config import settings


def get_fernet() -> Fernet:
    """
    Get Fernet cipher instance using the encryption key from settings.

    Returns:
        Fernet cipher instance
    """
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_api_key(api_key: str) -> Optional[str]:
    """
    Encrypt API key for secure storage in database.

    Args:
        api_key: Plain text API key

    Returns:
        Encrypted API key, or None if input is empty
    """
    if not api_key:
        return None

    fernet = get_fernet()
    encrypted = fernet.encrypt(api_key.encode())
    return encrypted.decode()


def decrypt_api_key(encrypted_key: str) -> Optional[str]:
    """
    Decrypt API key from database storage.

    Args:
        encrypted_key: Encrypted API key

    Returns:
        Plain text API key, or None if input is empty
    """
    if not encrypted_key:
        return None

    fernet = get_fernet()
    decrypted = fernet.decrypt(encrypted_key.encode())
    return decrypted.decode()
