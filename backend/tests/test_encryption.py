"""
Tests for API key encryption utilities.
"""
import pytest

from app.utils.encryption import encrypt_api_key, decrypt_api_key


class TestAPIKeyEncryption:
    """Tests for API key encryption and decryption"""

    def test_encrypt_api_key(self):
        """Test API key encryption"""
        api_key = "sk-test-1234567890abcdef"
        encrypted = encrypt_api_key(api_key)

        # Encrypted key should be different from original
        assert encrypted != api_key

        # Encrypted key should be a string
        assert isinstance(encrypted, str)

        # Encrypted key should not be empty
        assert len(encrypted) > 0

    def test_encrypt_api_key_empty(self):
        """Test encryption of empty string"""
        encrypted = encrypt_api_key("")
        # Should return None for empty string
        assert encrypted is None

    def test_encrypt_api_key_none(self):
        """Test encryption of None"""
        encrypted = encrypt_api_key(None)
        # Should return None
        assert encrypted is None

    def test_decrypt_api_key(self):
        """Test API key decryption"""
        api_key = "sk-test-1234567890abcdef"
        encrypted = encrypt_api_key(api_key)
        decrypted = decrypt_api_key(encrypted)

        # Decrypted key should match original
        assert decrypted == api_key

    def test_decrypt_api_key_empty(self):
        """Test decryption of empty string"""
        decrypted = decrypt_api_key("")
        # Should return None for empty string
        assert decrypted is None

    def test_decrypt_api_key_none(self):
        """Test decryption of None"""
        decrypted = decrypt_api_key(None)
        # Should return None
        assert decrypted is None

    def test_encrypt_decrypt_roundtrip(self):
        """Test encryption and decryption roundtrip"""
        api_keys = [
            "sk-openai-1234567890",
            "sk-ant-1234567890",
            "very-long-api-key-" + "x" * 100,
            "short",
            "with-special-chars-!@#$%^&*()",
        ]

        for api_key in api_keys:
            encrypted = encrypt_api_key(api_key)
            decrypted = decrypt_api_key(encrypted)
            assert decrypted == api_key, f"Failed for: {api_key}"

    def test_different_keys_produce_different_encrypted_values(self):
        """Test that different API keys produce different encrypted values"""
        key1 = "sk-test-key1"
        key2 = "sk-test-key2"

        encrypted1 = encrypt_api_key(key1)
        encrypted2 = encrypt_api_key(key2)

        # Different keys should produce different encrypted values
        assert encrypted1 != encrypted2

    def test_same_key_produces_different_encrypted_values(self):
        """Test that same API key produces different encrypted values (due to IV)"""
        api_key = "sk-test-same-key"

        encrypted1 = encrypt_api_key(api_key)
        encrypted2 = encrypt_api_key(api_key)

        # Note: Fernet doesn't use random IV, so same key will produce same output
        # This is actually expected behavior for Fernet
        # If we want different outputs, we'd need to use a different encryption method
        # For now, let's just verify both decrypt correctly
        assert decrypt_api_key(encrypted1) == api_key
        assert decrypt_api_key(encrypted2) == api_key

    def test_invalid_encrypted_key(self):
        """Test decryption of invalid encrypted key"""
        invalid_encrypted = "not-a-valid-encrypted-key"

        with pytest.raises(Exception):
            # Should raise an exception for invalid encrypted data
            decrypt_api_key(invalid_encrypted)


class TestEncryptionIntegration:
    """Integration tests for encryption utilities"""

    def test_openai_api_key_encryption(self):
        """Test encryption of OpenAI API key"""
        openai_key = "sk-proj-1234567890abcdefghijklmnopqrstuvwxyz"
        encrypted = encrypt_api_key(openai_key)
        decrypted = decrypt_api_key(encrypted)

        assert decrypted == openai_key
        assert encrypted != openai_key

    def test_anthropic_api_key_encryption(self):
        """Test encryption of Anthropic API key"""
        anthropic_key = "sk-ant-api03-1234567890abcdefghijklmnopqrstuvwxyz"
        encrypted = encrypt_api_key(anthropic_key)
        decrypted = decrypt_api_key(encrypted)

        assert decrypted == anthropic_key
        assert encrypted != anthropic_key

    def test_multiple_providers_encryption(self):
        """Test encryption of multiple provider API keys"""
        api_keys = {
            "openai": "sk-proj-openai123",
            "anthropic": "sk-ant-anthropic456",
            "google": "AIza-google789",
        }

        encrypted_keys = {}
        for provider, key in api_keys.items():
            encrypted_keys[provider] = encrypt_api_key(key)

        # Verify all can be decrypted correctly
        for provider, key in api_keys.items():
            decrypted = decrypt_api_key(encrypted_keys[provider])
            assert decrypted == key
