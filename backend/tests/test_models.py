"""
Tests for database models.
"""
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.security import hash_password


class TestUserModel:
    """Tests for User model"""

    def test_create_user(self, db):
        """Test creating a user"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=hash_password("password123"),
            is_active=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        # User should have an ID
        assert user.id is not None

        # User attributes should match
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True

        # Should have timestamps
        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)

    def test_user_defaults(self, db):
        """Test user model default values"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=hash_password("password123")
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        # is_active should default to True
        assert user.is_active is True

        # created_at should be set automatically
        assert user.created_at is not None

    def test_unique_username(self, db):
        """Test that username must be unique"""
        # Create first user
        user1 = User(
            username="testuser",
            email="test1@example.com",
            hashed_password=hash_password("password123")
        )
        db.add(user1)
        db.commit()

        # Try to create second user with same username
        user2 = User(
            username="testuser",  # Same username
            email="test2@example.com",
            hashed_password=hash_password("password123")
        )
        db.add(user2)

        # Should raise IntegrityError
        with pytest.raises(IntegrityError):
            db.commit()

    def test_unique_email(self, db):
        """Test that email must be unique"""
        # Create first user
        user1 = User(
            username="testuser1",
            email="test@example.com",
            hashed_password=hash_password("password123")
        )
        db.add(user1)
        db.commit()

        # Try to create second user with same email
        user2 = User(
            username="testuser2",
            email="test@example.com",  # Same email
            hashed_password=hash_password("password123")
        )
        db.add(user2)

        # Should raise IntegrityError
        with pytest.raises(IntegrityError):
            db.commit()

    def test_user_repr(self, db):
        """Test user string representation"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=hash_password("password123")
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        repr_str = repr(user)

        # Should contain user info
        assert "testuser" in repr_str
        assert "test@example.com" in repr_str
        assert str(user.id) in repr_str

    def test_query_user_by_username(self, db, test_user):
        """Test querying user by username"""
        user = db.query(User).filter(User.username == "testuser").first()

        assert user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_query_user_by_email(self, db, test_user):
        """Test querying user by email"""
        user = db.query(User).filter(User.email == "test@example.com").first()

        assert user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_query_nonexistent_user(self, db):
        """Test querying for non-existent user"""
        user = db.query(User).filter(User.username == "nonexistent").first()

        assert user is None

    def test_update_user(self, db, test_user):
        """Test updating user attributes"""
        user = db.query(User).filter(User.username == "testuser").first()

        # Update email
        user.email = "newemail@example.com"
        db.commit()
        db.refresh(user)

        # Verify update
        assert user.email == "newemail@example.com"

        # updated_at should be set
        assert user.updated_at is not None

    def test_delete_user(self, db, test_user):
        """Test deleting a user"""
        user_id = test_user.id

        # Delete user
        db.delete(test_user)
        db.commit()

        # User should not exist
        user = db.query(User).filter(User.id == user_id).first()
        assert user is None

    def test_inactive_user(self, db):
        """Test creating inactive user"""
        user = User(
            username="inactiveuser",
            email="inactive@example.com",
            hashed_password=hash_password("password123"),
            is_active=False
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.is_active is False

    def test_multiple_users(self, db):
        """Test creating multiple users"""
        users = [
            User(
                username=f"user{i}",
                email=f"user{i}@example.com",
                hashed_password=hash_password("password123")
            )
            for i in range(5)
        ]

        for user in users:
            db.add(user)

        db.commit()

        # Query all users
        all_users = db.query(User).all()

        # Should have all 5 users
        assert len(all_users) == 5

        # All should have unique usernames and emails
        usernames = [u.username for u in all_users]
        emails = [u.email for u in all_users]

        assert len(set(usernames)) == 5
        assert len(set(emails)) == 5


class TestUserModelValidation:
    """Tests for User model validation"""

    def test_user_without_username(self, db):
        """Test that user cannot be created without username"""
        user = User(
            email="test@example.com",
            hashed_password=hash_password("password123")
        )

        db.add(user)

        # Should raise IntegrityError (NOT NULL constraint)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_user_without_email(self, db):
        """Test that user cannot be created without email"""
        user = User(
            username="testuser",
            hashed_password=hash_password("password123")
        )

        db.add(user)

        # Should raise IntegrityError (NOT NULL constraint)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_user_without_password(self, db):
        """Test that user cannot be created without password"""
        user = User(
            username="testuser",
            email="test@example.com"
        )

        db.add(user)

        # Should raise IntegrityError (NOT NULL constraint)
        with pytest.raises(IntegrityError):
            db.commit()
