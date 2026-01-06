"""
Encryption utilities for securing sensitive data like API keys.

Uses Fernet (symmetric encryption) for encrypting API keys at rest.
The encryption key is derived from the SECRET_KEY in settings.
"""
from cryptography.fernet import Fernet
from .config import settings


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data.

    Uses Fernet symmetric encryption with the ENCRYPTION_KEY from settings.
    """

    def __init__(self):
        """Initialize the encryption service with the configured key."""
        # Use the ENCRYPTION_KEY directly from settings
        # This should be a valid Fernet key (32 url-safe base64-encoded bytes)
        self.fernet = Fernet(settings.ENCRYPTION_KEY.encode())

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""

        encrypted_bytes = self.fernet.encrypt(plaintext.encode())
        return encrypted_bytes.decode()

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            encrypted: The base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
        """
        if not encrypted:
            return ""

        decrypted_bytes = self.fernet.decrypt(encrypted.encode())
        return decrypted_bytes.decode()


# Singleton instance
_encryption_service = None


def get_encryption_service() -> EncryptionService:
    """
    Get the singleton encryption service instance.

    Returns:
        EncryptionService instance
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt_api_key(api_key: str) -> str:
    """
    Convenience function to encrypt an API key.

    Args:
        api_key: The API key to encrypt

    Returns:
        Encrypted API key
    """
    service = get_encryption_service()
    return service.encrypt(api_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Convenience function to decrypt an API key.

    Args:
        encrypted_key: The encrypted API key

    Returns:
        Decrypted API key
    """
    service = get_encryption_service()
    return service.decrypt(encrypted_key)
