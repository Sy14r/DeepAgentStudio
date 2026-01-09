"""
Test configuration and fixtures for DeepAgentStudio backend tests.

This module supports both PostgreSQL (recommended for full testing) and SQLite
(for quick unit tests that don't require PostgreSQL-specific features).

Set TEST_DATABASE_URL environment variable to use PostgreSQL:
    export TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/testdb
"""
import os
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.llm_provider import LLMProviderConfig, LLMProviderType
from app.models.mcp_server import MCPServerConfig, MCPTransportType
from app.security import hash_password
from app.encryption import encrypt_api_key

# Check for PostgreSQL test database URL
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

if TEST_DATABASE_URL:
    # Use PostgreSQL for testing (supports JSONB, ARRAY, etc.)
    engine = create_engine(TEST_DATABASE_URL)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    USE_POSTGRES = True
else:
    # Fall back to SQLite for basic tests
    # Note: Tests using PostgreSQL-specific types (JSONB) will fail with SQLite
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key constraints for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    USE_POSTGRES = False


@pytest.fixture(scope="function")
def db():
    """
    Create a fresh database for each test.

    Yields:
        Database session for testing
    """
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create a new session for the test
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()

        if USE_POSTGRES:
            # PostgreSQL: Truncate all tables for clean state
            with engine.connect() as conn:
                # Disable foreign key checks temporarily
                conn.execute(text("SET session_replication_role = 'replica'"))
                # Get all table names and truncate
                for table in reversed(Base.metadata.sorted_tables):
                    try:
                        conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
                    except Exception:
                        pass  # Table might not exist yet
                # Re-enable foreign key checks
                conn.execute(text("SET session_replication_role = 'origin'"))
                conn.commit()
        else:
            # SQLite: Drop and recreate tables
            with engine.connect() as conn:
                conn.execute(text("PRAGMA foreign_keys=OFF"))
                conn.commit()
            Base.metadata.drop_all(bind=engine)
            with engine.connect() as conn:
                conn.execute(text("PRAGMA foreign_keys=ON"))
                conn.commit()


@pytest.fixture(scope="function")
def client(db):
    """
    Create a test client with database dependency override.

    Args:
        db: Database session fixture

    Yields:
        TestClient for making API requests
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass

    # Override the database dependency
    app.dependency_overrides[get_db] = override_get_db

    # Create test client
    with TestClient(app) as test_client:
        yield test_client

    # Clear overrides after test
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db):
    """
    Create a test user in the database.

    Args:
        db: Database session fixture

    Returns:
        Created user object
    """
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def second_test_user(db):
    """
    Create a second test user in the database.

    Args:
        db: Database session fixture

    Returns:
        Created user object
    """
    user = User(
        username="testuser2",
        email="test2@example.com",
        hashed_password=hash_password("testpassword456"),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_user_token(client, test_user):
    """
    Create a test user and return authentication token.

    Args:
        client: Test client fixture
        test_user: Test user fixture

    Returns:
        JWT access token for the test user
    """
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def auth_headers(test_user_token):
    """
    Create authorization headers with test user token.

    Args:
        test_user_token: JWT token fixture

    Returns:
        Dictionary with Authorization header
    """
    return {"Authorization": f"Bearer {test_user_token}"}


# Test data fixtures
@pytest.fixture
def valid_user_data():
    """Valid user registration data"""
    return {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "securepassword123"
    }


@pytest.fixture
def invalid_user_data():
    """Invalid user registration data (short password)"""
    return {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "short"
    }


@pytest.fixture
def duplicate_username_data(test_user):
    """User data with duplicate username"""
    return {
        "username": "testuser",  # Same as test_user
        "email": "different@example.com",
        "password": "securepassword123"
    }


@pytest.fixture
def duplicate_email_data(test_user):
    """User data with duplicate email"""
    return {
        "username": "differentuser",
        "email": "test@example.com",  # Same as test_user
        "password": "securepassword123"
    }


@pytest.fixture(scope="function")
def test_llm_provider(db, test_user):
    """
    Create a test LLM provider configuration.

    Args:
        db: Database session fixture
        test_user: Test user fixture

    Returns:
        Created LLM provider config object
    """
    provider = LLMProviderConfig(
        user_id=test_user.id,
        provider_type=LLMProviderType.OPENAI,
        name="Test OpenAI Provider",
        description="A test OpenAI provider for testing",
        encrypted_api_key=encrypt_api_key("sk-test-key-12345"),
        config={"default_model": "gpt-4"},
        is_active=True
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


@pytest.fixture(scope="function")
def test_anthropic_provider(db, test_user):
    """
    Create a test Anthropic LLM provider configuration.

    Args:
        db: Database session fixture
        test_user: Test user fixture

    Returns:
        Created LLM provider config object
    """
    provider = LLMProviderConfig(
        user_id=test_user.id,
        provider_type=LLMProviderType.ANTHROPIC,
        name="Test Anthropic Provider",
        description="A test Anthropic provider for testing",
        encrypted_api_key=encrypt_api_key("sk-ant-test-key-12345"),
        config={"default_model": "claude-3-opus-20240229"},
        is_active=True
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


@pytest.fixture(scope="function")
def test_mcp_server_stdio(db, test_user):
    """
    Create a test stdio MCP server configuration.

    Args:
        db: Database session fixture
        test_user: Test user fixture

    Returns:
        Created MCP server config object
    """
    import json
    server = MCPServerConfig(
        user_id=test_user.id,
        name="Test Stdio MCP Server",
        description="A test stdio MCP server for testing",
        transport_type=MCPTransportType.STDIO,
        stdio_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-test"]
        },
        encrypted_env_vars=encrypt_api_key(json.dumps({"TEST_VAR": "test_value"})),
        config={},
        is_active=True
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    return server


@pytest.fixture(scope="function")
def test_mcp_server_sse(db, test_user):
    """
    Create a test SSE MCP server configuration.

    Args:
        db: Database session fixture
        test_user: Test user fixture

    Returns:
        Created MCP server config object
    """
    server = MCPServerConfig(
        user_id=test_user.id,
        name="Test SSE MCP Server",
        description="A test SSE MCP server for testing",
        transport_type=MCPTransportType.SSE,
        http_config={
            "url": "http://localhost:3000/mcp",
            "headers": {"Authorization": "Bearer test-token"}
        },
        config={},
        is_active=True
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    return server
