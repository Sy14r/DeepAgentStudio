# DeepAgentStudio Test Suite

Comprehensive testing suite for Phase 1 backend implementation.

## Test Coverage

### test_security.py
Tests for authentication and security utilities:
- Password hashing (bcrypt)
- Password verification
- JWT token creation
- JWT token decoding
- Token expiration
- Invalid token handling

### test_encryption.py
Tests for API key encryption utilities:
- API key encryption (Fernet)
- API key decryption
- Roundtrip encryption/decryption
- Handling of empty/None values
- Invalid encrypted key handling
- Multiple provider API keys

### test_models.py
Tests for database models:
- User model creation
- User model defaults
- Unique constraints (username, email)
- User queries (by username, email)
- User updates
- User deletion
- Multiple users
- Field validation (NOT NULL constraints)

### test_auth.py
Tests for authentication API endpoints:
- **Health Endpoints**: Root and health check
- **User Registration**: Success, duplicate username/email, validation
- **User Login**: Success, wrong password, inactive user, missing fields
- **Get Current User**: Valid token, invalid token, expired token
- **Integration**: Complete auth flow, multiple users isolation

### conftest.py
Test configuration and fixtures:
- Database setup (in-memory SQLite)
- Test client with dependency overrides
- Test user fixture
- Authentication token fixtures
- Test data fixtures

## Running Tests

### In Docker (Recommended)

```bash
# Start services (if not already running)
docker compose up -d

# Run all tests
docker compose exec backend pytest

# Run with verbose output
docker compose exec backend pytest -v

# Run specific test file
docker compose exec backend pytest tests/test_auth.py

# Run specific test class
docker compose exec backend pytest tests/test_auth.py::TestUserLogin

# Run specific test function
docker compose exec backend pytest tests/test_auth.py::TestUserLogin::test_login_success

# Run with coverage
docker compose exec backend pytest --cov=app --cov-report=html

# Run tests with markers
docker compose exec backend pytest -m auth
docker compose exec backend pytest -m security
```

### Using Test Runner Script

```bash
# Make sure you're in the backend directory
cd backend

# Run all tests
docker compose exec backend ./run_tests.sh

# Run with coverage
docker compose exec backend ./run_tests.sh --coverage

# Run specific test file
docker compose exec backend ./run_tests.sh --test test_auth.py

# Verbose output
docker compose exec backend ./run_tests.sh --verbose

# Help
docker compose exec backend ./run_tests.sh --help
```

### Locally (Without Docker)

```bash
# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Set environment variables
export DATABASE_URL="sqlite:///./test.db"
export JWT_SECRET_KEY="test-secret-key"
export ENCRYPTION_KEY="test-encryption-key"
export JWT_ALGORITHM="HS256"
export ACCESS_TOKEN_EXPIRE_MINUTES="30"

# Run tests
cd backend
pytest

# Or use the test runner
./run_tests.sh
```

## Test Markers

Tests are organized with markers for selective execution:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.security` - Security-related tests
- `@pytest.mark.models` - Database model tests

Run specific markers:
```bash
pytest -m auth        # Run only auth tests
pytest -m security    # Run only security tests
pytest -m models      # Run only model tests
```

## Test Statistics

**Total Test Files**: 4
**Estimated Total Tests**: 70+

Breakdown:
- test_security.py: ~15 tests
- test_encryption.py: ~15 tests
- test_models.py: ~20 tests
- test_auth.py: ~25 tests

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    docker compose up -d
    docker compose exec -T backend pytest --cov=app
```

## Coverage Goals

Target coverage: **90%+**

Generate coverage report:
```bash
docker compose exec backend pytest --cov=app --cov-report=html
```

View coverage report at: `htmlcov/index.html`

## Writing New Tests

### Test Structure

```python
class TestFeatureName:
    """Tests for specific feature"""

    def test_success_case(self, client):
        """Test successful operation"""
        response = client.get("/endpoint")
        assert response.status_code == 200

    def test_failure_case(self, client):
        """Test failure scenario"""
        response = client.get("/invalid")
        assert response.status_code == 404
```

### Using Fixtures

```python
def test_with_authenticated_user(self, client, auth_headers):
    """Test endpoint requiring authentication"""
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
```

### Database Tests

```python
def test_create_model(self, db):
    """Test creating a database model"""
    obj = MyModel(field="value")
    db.add(obj)
    db.commit()
    db.refresh(obj)
    assert obj.id is not None
```

## Troubleshooting

### Tests Failing Due to Database

If tests fail with database errors:
```bash
# Rebuild backend container
docker compose up -d --build backend

# Clear test database
docker compose exec backend rm -f test.db
```

### Import Errors

Ensure you're running tests from the backend directory:
```bash
cd backend
pytest
```

### Environment Variable Issues

Tests use in-memory SQLite and don't require actual environment variables, but the config module needs them to be set. The test fixtures handle this automatically.

## Next Steps

As new features are added:
1. Add corresponding test files (e.g., `test_agents.py`)
2. Update this README with new test descriptions
3. Maintain test coverage above 90%
4. Add integration tests for complex workflows
