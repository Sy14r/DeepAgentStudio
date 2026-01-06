"""
Tests for authentication API endpoints.
"""
import pytest
from app.models.user import User


class TestHealthEndpoints:
    """Tests for basic health check endpoints"""

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "DeepAgentStudio API"
        assert data["version"] == "0.1.0"
        assert data["docs"] == "/docs"

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestUserRegistration:
    """Tests for user registration endpoint"""

    def test_register_user_success(self, client, valid_user_data):
        """Test successful user registration"""
        response = client.post(
            "/api/v1/auth/register",
            json=valid_user_data
        )

        assert response.status_code == 201
        data = response.json()

        # Should return user data
        assert data["username"] == valid_user_data["username"]
        assert data["email"] == valid_user_data["email"]
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

        # Should NOT return password
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_user_duplicate_username(self, client, duplicate_username_data):
        """Test registration with duplicate username"""
        response = client.post(
            "/api/v1/auth/register",
            json=duplicate_username_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "already registered" in data["detail"].lower()

    def test_register_user_duplicate_email(self, client, duplicate_email_data):
        """Test registration with duplicate email"""
        response = client.post(
            "/api/v1/auth/register",
            json=duplicate_email_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "already registered" in data["detail"].lower()

    def test_register_user_invalid_email(self, client):
        """Test registration with invalid email format"""
        invalid_data = {
            "username": "testuser",
            "email": "not-an-email",
            "password": "password12345"
        }

        response = client.post(
            "/api/v1/auth/register",
            json=invalid_data
        )

        assert response.status_code == 422  # Validation error

    def test_register_user_short_password(self, client, invalid_user_data):
        """Test registration with too short password"""
        response = client.post(
            "/api/v1/auth/register",
            json=invalid_user_data
        )

        assert response.status_code == 422  # Validation error

    def test_register_user_short_username(self, client):
        """Test registration with too short username"""
        short_username_data = {
            "username": "ab",  # Only 2 characters
            "email": "test@example.com",
            "password": "password12345"
        }

        response = client.post(
            "/api/v1/auth/register",
            json=short_username_data
        )

        assert response.status_code == 422  # Validation error

    def test_register_user_missing_fields(self, client):
        """Test registration with missing required fields"""
        # Missing password
        incomplete_data = {
            "username": "testuser",
            "email": "test@example.com"
        }

        response = client.post(
            "/api/v1/auth/register",
            json=incomplete_data
        )

        assert response.status_code == 422  # Validation error


class TestUserLogin:
    """Tests for user login endpoint"""

    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "testpassword123"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should return access token
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Token should not be empty
        assert len(data["access_token"]) > 0

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert "incorrect" in data["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent",
                "password": "password12345"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert "incorrect" in data["detail"].lower()

    def test_login_inactive_user(self, client, db):
        """Test login with inactive user"""
        # Create inactive user
        from app.security import hash_password
        inactive_user = User(
            username="inactiveuser",
            email="inactive@example.com",
            hashed_password=hash_password("password12345"),
            is_active=False
        )
        db.add(inactive_user)
        db.commit()

        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "inactiveuser",
                "password": "password12345"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "inactive" in data["detail"].lower()

    def test_login_missing_username(self, client):
        """Test login with missing username"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "password": "password12345"
            }
        )

        assert response.status_code == 422  # Validation error

    def test_login_missing_password(self, client):
        """Test login with missing password"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser"
            }
        )

        assert response.status_code == 422  # Validation error


class TestGetCurrentUser:
    """Tests for get current user endpoint"""

    def test_get_current_user_success(self, client, test_user, auth_headers):
        """Test getting current user with valid token"""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return user data
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["is_active"] is True
        assert "id" in data

        # Should NOT return password
        assert "password" not in data
        assert "hashed_password" not in data

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token"""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401

    def test_get_current_user_malformed_header(self, client, test_user_token):
        """Test getting current user with malformed authorization header"""
        # Missing "Bearer" prefix
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": test_user_token}
        )

        assert response.status_code == 401

    def test_get_current_user_expired_token(self, client, test_user):
        """Test getting current user with expired token"""
        from datetime import timedelta
        from app.security import create_access_token

        # Create token that expires immediately
        expired_token = create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(seconds=-1)  # Negative expiration
        )

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401


class TestAuthenticationFlow:
    """Integration tests for complete authentication flow"""

    def test_complete_auth_flow(self, client):
        """Test complete flow: register -> login -> get user"""
        # Step 1: Register
        register_data = {
            "username": "flowuser",
            "email": "flow@example.com",
            "password": "flowpassword123"
        }

        register_response = client.post(
            "/api/v1/auth/register",
            json=register_data
        )

        assert register_response.status_code == 201
        user_data = register_response.json()
        user_id = user_data["id"]

        # Step 2: Login
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "flowuser",
                "password": "flowpassword123"
            }
        )

        assert login_response.status_code == 200
        token_data = login_response.json()
        access_token = token_data["access_token"]

        # Step 3: Get current user
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert me_response.status_code == 200
        current_user = me_response.json()

        # Verify it's the same user
        assert current_user["id"] == user_id
        assert current_user["username"] == "flowuser"
        assert current_user["email"] == "flow@example.com"

    def test_multiple_users_isolation(self, client):
        """Test that multiple users are properly isolated"""
        # Create user 1
        user1_data = {
            "username": "user1",
            "email": "user1@example.com",
            "password": "password12345"
        }
        client.post("/api/v1/auth/register", json=user1_data)

        # Create user 2
        user2_data = {
            "username": "user2",
            "email": "user2@example.com",
            "password": "password12345"
        }
        client.post("/api/v1/auth/register", json=user2_data)

        # Login as user 1
        login1_response = client.post(
            "/api/v1/auth/login",
            data={"username": "user1", "password": "password12345"}
        )
        token1 = login1_response.json()["access_token"]

        # Login as user 2
        login2_response = client.post(
            "/api/v1/auth/login",
            data={"username": "user2", "password": "password12345"}
        )
        token2 = login2_response.json()["access_token"]

        # Get user info with token 1
        me1_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token1}"}
        )
        user1_info = me1_response.json()

        # Get user info with token 2
        me2_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token2}"}
        )
        user2_info = me2_response.json()

        # Verify each token returns correct user
        assert user1_info["username"] == "user1"
        assert user2_info["username"] == "user2"
        assert user1_info["id"] != user2_info["id"]
