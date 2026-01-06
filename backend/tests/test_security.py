"""
Tests for security utilities (password hashing and JWT tokens).
"""
import pytest
from datetime import timedelta
from jose import jwt

from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)
from app.config import settings


class TestPasswordHashing:
    """Tests for password hashing functions"""

    def test_hash_password(self):
        """Test that password hashing works"""
        password = "mypassword123"
        hashed = hash_password(password)

        # Hash should be different from password
        assert hashed != password

        # Hash should be a string
        assert isinstance(hashed, str)

        # Hash should not be empty
        assert len(hashed) > 0

    def test_hash_password_different_hashes(self):
        """Test that same password produces different hashes (due to salt)"""
        password = "mypassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to random salt
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "mypassword123"
        hashed = hash_password(password)

        # Verification should succeed
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "mypassword123"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)

        # Verification should fail
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """Test password verification with empty password"""
        password = "mypassword123"
        hashed = hash_password(password)

        # Verification with empty password should fail
        assert verify_password("", hashed) is False


class TestJWTTokens:
    """Tests for JWT token creation and decoding"""

    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "testuser"}
        token = create_access_token(data)

        # Token should be a string
        assert isinstance(token, str)

        # Token should not be empty
        assert len(token) > 0

        # Token should have 3 parts (header.payload.signature)
        assert token.count('.') == 2

    def test_create_access_token_with_expiration(self):
        """Test JWT token creation with custom expiration"""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta)

        # Decode without verification to check expiration
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # Should have expiration claim
        assert "exp" in payload

    def test_decode_access_token_valid(self):
        """Test decoding valid JWT token"""
        data = {"sub": "testuser"}
        token = create_access_token(data)

        # Decode token
        payload = decode_access_token(token)

        # Payload should not be None
        assert payload is not None

        # Should contain original data
        assert payload["sub"] == "testuser"

        # Should have expiration
        assert "exp" in payload

    def test_decode_access_token_invalid(self):
        """Test decoding invalid JWT token"""
        invalid_token = "invalid.token.here"

        # Should return None for invalid token
        payload = decode_access_token(invalid_token)
        assert payload is None

    def test_decode_access_token_wrong_secret(self):
        """Test decoding token with wrong secret"""
        data = {"sub": "testuser"}
        # Create token with different secret
        token = jwt.encode(data, "wrong-secret", algorithm=settings.JWT_ALGORITHM)

        # Should return None when decoded with correct secret
        payload = decode_access_token(token)
        assert payload is None

    def test_decode_access_token_empty(self):
        """Test decoding empty token"""
        payload = decode_access_token("")
        assert payload is None

    def test_token_contains_correct_data(self):
        """Test that token contains all expected data"""
        data = {"sub": "testuser", "email": "test@example.com"}
        token = create_access_token(data)

        payload = decode_access_token(token)

        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["email"] == "test@example.com"


class TestSecurityIntegration:
    """Integration tests for security functions"""

    def test_password_and_token_workflow(self):
        """Test complete workflow: hash password, create token, verify"""
        # Step 1: Hash password
        password = "userpassword123"
        hashed = hash_password(password)

        # Step 2: Verify password (simulating login)
        assert verify_password(password, hashed) is True

        # Step 3: Create token after successful verification
        token = create_access_token({"sub": "testuser"})

        # Step 4: Decode token
        payload = decode_access_token(token)

        # All steps should succeed
        assert payload is not None
        assert payload["sub"] == "testuser"
