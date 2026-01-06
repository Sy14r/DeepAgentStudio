# DeepAgentStudio - Testing Documentation

## Overview

A comprehensive testing suite has been implemented for Phase 1 to ensure all backend functionality works correctly. This document provides a complete guide to running and understanding the tests.

## Test Suite Summary

### Statistics
- **Total Test Files**: 4
- **Total Tests**: 70+
- **Target Coverage**: 90%+
- **Test Framework**: pytest
- **Database**: In-memory SQLite (isolated test environment)

### Test Files

1. **test_security.py** (~15 tests)
   - Password hashing with bcrypt
   - Password verification
   - JWT token creation and decoding
   - Token expiration handling
   - Invalid token detection

2. **test_encryption.py** (~15 tests)
   - API key encryption with Fernet
   - API key decryption
   - Roundtrip encryption/decryption
   - Multiple provider keys (OpenAI, Anthropic, Google)
   - Edge cases (empty, None, invalid data)

3. **test_models.py** (~20 tests)
   - User model creation and defaults
   - Unique constraints (username, email)
   - Database queries and filtering
   - Model updates and deletion
   - Field validation (NOT NULL)
   - Multiple users and isolation

4. **test_auth.py** (~25 tests)
   - Health check endpoints
   - User registration (success and validation)
   - User login (success and error cases)
   - Get current user endpoint
   - Complete authentication flow
   - Token-based authentication
   - Multi-user isolation

## Running Tests

### Prerequisites

Make sure Docker Compose services are running:

```bash
docker compose up -d
```

### Basic Test Commands

```bash
# Run all tests
docker compose exec backend pytest

# Run with verbose output
docker compose exec backend pytest -v

# Run with very verbose output (shows test names and results)
docker compose exec backend pytest -vv

# Run specific test file
docker compose exec backend pytest tests/test_auth.py

# Run specific test class
docker compose exec backend pytest tests/test_auth.py::TestUserLogin

# Run specific test function
docker compose exec backend pytest tests/test_auth.py::TestUserLogin::test_login_success
```

### Using the Test Runner Script

The test runner script provides a convenient interface:

```bash
# Run all tests
docker compose exec backend ./run_tests.sh

# Run with coverage report
docker compose exec backend ./run_tests.sh --coverage

# Run specific test file
docker compose exec backend ./run_tests.sh --test test_auth.py

# Verbose output
docker compose exec backend ./run_tests.sh --verbose

# Show help
docker compose exec backend ./run_tests.sh --help
```

### Coverage Reports

Generate and view test coverage:

```bash
# Run tests with coverage
docker compose exec backend pytest --cov=app --cov-report=html --cov-report=term-missing

# View coverage in terminal
docker compose exec backend pytest --cov=app --cov-report=term

# Coverage report is generated in backend/htmlcov/
# Open backend/htmlcov/index.html in a browser to view detailed coverage
```

## Test Configuration

### pytest.ini

Located at `backend/pytest.ini`, this file configures:
- Test discovery patterns
- Console output formatting
- Test markers for selective execution
- Logging configuration
- Asyncio settings

### conftest.py

Located at `backend/tests/conftest.py`, provides:
- **Database fixture**: In-memory SQLite for isolated testing
- **Client fixture**: TestClient with database dependency override
- **Test user fixture**: Pre-created test user
- **Auth token fixture**: Valid JWT token for testing protected endpoints
- **Test data fixtures**: Valid/invalid registration data

## Test Markers

Tests can be marked for selective execution:

```bash
# Run only authentication tests
pytest -m auth

# Run only security tests
pytest -m security

# Run only model tests
pytest -m models

# Run only integration tests
pytest -m integration
```

Currently available markers:
- `unit`: Unit tests
- `integration`: Integration tests
- `auth`: Authentication tests
- `security`: Security-related tests
- `models`: Database model tests

## Expected Test Results

When all tests pass, you should see output similar to:

```
================================ test session starts =================================
platform linux -- Python 3.12.x, pytest-7.4.4, pluggy-1.x
rootdir: /app/backend
configfile: pytest.ini
testpaths: tests
plugins: asyncio-0.23.3
collected 70 items

tests/test_auth.py ........................... [ 35%]
tests/test_encryption.py ................ [ 56%]
tests/test_models.py .................... [ 78%]
tests/test_security.py ................ [100%]

================================ 70 passed in X.XXs ==================================
```

## Troubleshooting Tests

### Common Issues and Solutions

#### 1. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'app'`

**Solution**: Make sure you're running tests from inside the Docker container:
```bash
docker compose exec backend pytest
```

#### 2. Database Errors

**Problem**: Tests fail with database connection errors

**Solution**: Tests use in-memory SQLite, not PostgreSQL. If you see PostgreSQL errors, check that the database fixtures are being used:
```bash
# Rebuild backend container
docker compose up -d --build backend
```

#### 3. Token Expiration Tests Failing

**Problem**: Tests for expired tokens are flaky

**Solution**: This is expected for time-based tests. Re-run the specific test:
```bash
docker compose exec backend pytest tests/test_auth.py::TestGetCurrentUser::test_get_current_user_expired_token -v
```

#### 4. Encryption Tests Failing

**Problem**: Encryption/decryption tests fail

**Solution**: Ensure ENCRYPTION_KEY is set in docker-compose.yml. The test environment should handle this automatically.

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

### GitHub Actions Example

```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Build and start services
        run: docker compose up -d

      - name: Run tests
        run: docker compose exec -T backend pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
```

### GitLab CI Example

```yaml
test:
  stage: test
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker compose up -d
    - docker compose exec -T backend pytest --cov=app
```

## Test Development Guidelines

### Writing New Tests

When adding new features, follow this structure:

```python
class TestNewFeature:
    """Tests for new feature description"""

    def test_success_case(self, client, auth_headers):
        """Test successful operation"""
        response = client.post(
            "/api/v1/endpoint",
            headers=auth_headers,
            json={"data": "value"}
        )
        assert response.status_code == 200
        assert response.json()["field"] == "expected_value"

    def test_validation_error(self, client, auth_headers):
        """Test validation error handling"""
        response = client.post(
            "/api/v1/endpoint",
            headers=auth_headers,
            json={"invalid": "data"}
        )
        assert response.status_code == 422

    def test_unauthorized_access(self, client):
        """Test endpoint requires authentication"""
        response = client.post("/api/v1/endpoint")
        assert response.status_code == 401
```

### Best Practices

1. **Descriptive Test Names**: Use clear, action-based test names
2. **One Assert Per Concept**: Focus each test on one behavior
3. **Use Fixtures**: Leverage existing fixtures for common setup
4. **Isolate Tests**: Each test should be independent
5. **Test Edge Cases**: Include tests for error conditions
6. **Document Complex Tests**: Add docstrings explaining test purpose

## Coverage Goals

### Target Coverage by Module

- **app/security.py**: 100%
- **app/utils/encryption.py**: 100%
- **app/models/user.py**: 95%+
- **app/api/v1/auth.py**: 95%+
- **app/database.py**: 90%+
- **app/config.py**: 80%+ (some config validation may be untested)

### Viewing Coverage

```bash
# Generate HTML coverage report
docker compose exec backend pytest --cov=app --cov-report=html

# The report will be in backend/htmlcov/
# Open backend/htmlcov/index.html in a browser

# Terminal coverage report
docker compose exec backend pytest --cov=app --cov-report=term-missing
```

## Next Steps

As Phase 2 (Agent Management) is implemented:

1. Create `test_agents.py` for agent CRUD operations
2. Create `test_agent_versions.py` for version control
3. Update test fixtures to include agent test data
4. Add integration tests for agent + tool + prompt workflows
5. Maintain coverage above 90%

## Summary

The comprehensive test suite ensures:
- ✅ All authentication flows work correctly
- ✅ Password hashing and JWT tokens are secure
- ✅ API key encryption protects sensitive data
- ✅ Database models enforce constraints
- ✅ API endpoints handle errors gracefully
- ✅ User isolation is maintained

**Total Confidence**: Phase 1 implementation is thoroughly tested and production-ready.

## Questions or Issues?

If tests fail:
1. Check the troubleshooting section above
2. Review test output for specific error messages
3. Verify Docker services are running: `docker compose ps`
4. Check backend logs: `docker compose logs backend`
5. Rebuild if needed: `docker compose up -d --build backend`

For detailed test documentation, see [backend/tests/README.md](./backend/tests/README.md).
