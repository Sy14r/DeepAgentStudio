# Phase 1 Verification Guide

This guide walks you through verifying that the Phase 1 implementation is working correctly using the comprehensive test suite.

## Quick Verification (5 minutes)

### Step 1: Start Services

```bash
cd /home/gpamerleau/Projects/DeepAgentStudio

# Start Docker Compose services
sudo docker-compose up -d

# Wait for services to be healthy (about 10 seconds)
sleep 10

# Check service status
sudo docker-compose ps
```

Expected output:
```
NAME                   STATUS
deepagent_backend      Up (healthy)
deepagent_postgres     Up (healthy)
```

### Step 2: View Backend Logs

```bash
sudo docker-compose logs backend
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 3: Run All Tests

```bash
docker compose exec backend pytest -v
```

Expected result:
```
================================ test session starts =================================
...
tests/test_auth.py::TestHealthEndpoints::test_root_endpoint PASSED
tests/test_auth.py::TestHealthEndpoints::test_health_endpoint PASSED
tests/test_auth.py::TestUserRegistration::test_register_user_success PASSED
...
================================ 70 passed in X.XXs ==================================
```

### Step 4: Generate Coverage Report

```bash
docker compose exec backend pytest --cov=app --cov-report=term-missing
```

Expected coverage: **90%+**

## Detailed Verification (15 minutes)

### Test Each Component Separately

#### 1. Test Security Utilities

```bash
docker compose exec backend pytest tests/test_security.py -v
```

Expected: **All 15 tests pass**

Verifies:
- Password hashing and verification
- JWT token creation and decoding
- Token expiration handling

#### 2. Test Encryption Utilities

```bash
docker compose exec backend pytest tests/test_encryption.py -v
```

Expected: **All 15 tests pass**

Verifies:
- API key encryption/decryption
- Handling of multiple providers
- Edge cases and error handling

#### 3. Test Database Models

```bash
docker compose exec backend pytest tests/test_models.py -v
```

Expected: **All 20 tests pass**

Verifies:
- User model creation and validation
- Unique constraints
- Database queries
- Model updates and deletion

#### 4. Test Authentication Endpoints

```bash
docker compose exec backend pytest tests/test_auth.py -v
```

Expected: **All 25 tests pass**

Verifies:
- User registration
- User login
- Token-based authentication
- Complete auth flows

### Test Specific Features

#### Test User Registration

```bash
docker compose exec backend pytest tests/test_auth.py::TestUserRegistration -v
```

Should show all registration scenarios passing:
- ✅ Successful registration
- ✅ Duplicate username rejection
- ✅ Duplicate email rejection
- ✅ Email validation
- ✅ Password length validation
- ✅ Username length validation

#### Test User Login

```bash
docker compose exec backend pytest tests/test_auth.py::TestUserLogin -v
```

Should show all login scenarios passing:
- ✅ Successful login
- ✅ Wrong password rejection
- ✅ Non-existent user rejection
- ✅ Inactive user rejection

#### Test Authentication Flow

```bash
docker compose exec backend pytest tests/test_auth.py::TestAuthenticationFlow -v
```

Should show complete workflows passing:
- ✅ Register → Login → Get User
- ✅ Multiple user isolation

## Manual API Verification (Optional)

If you want to manually verify the API is working:

### 1. Check Health Endpoint

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"healthy"}`

### 2. Register a User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "manualtest",
    "email": "manual@test.com",
    "password": "testpassword123"
  }'
```

Expected: User object with `id`, `username`, `email`, `is_active`, `created_at`

### 3. Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=manualtest&password=testpassword123"
```

Expected: `{"access_token":"eyJ...","token_type":"bearer"}`

### 4. Get Current User

```bash
# Replace <TOKEN> with the access_token from step 3
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <TOKEN>"
```

Expected: User object for "manualtest"

## Database Verification

### Connect to Database

```bash
docker compose exec postgres psql -U deepagent -d deepagentstudio
```

### Check Tables

```sql
-- List all tables
\dt

-- Expected tables:
-- users
-- alembic_version
```

### View Users

```sql
SELECT id, username, email, is_active, created_at FROM users;
```

### Exit PostgreSQL

```sql
\q
```

## Coverage Report Verification

### Generate HTML Coverage Report

```bash
docker compose exec backend pytest --cov=app --cov-report=html
```

### View Coverage

The coverage report is generated at `backend/htmlcov/index.html`

Open it in a browser to see:
- **Overall coverage**: Should be 90%+
- **File-by-file breakdown**
- **Line-by-line coverage** (which lines are tested)

### Coverage Breakdown

Expected coverage by module:
- `app/security.py`: ~100%
- `app/utils/encryption.py`: ~100%
- `app/models/user.py`: ~95%
- `app/api/v1/auth.py`: ~95%
- `app/database.py`: ~90%
- `app/config.py`: ~80%

## Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker ps

# View detailed logs
docker compose logs

# Rebuild and restart
docker compose down
docker compose up -d --build
```

### Tests Fail

```bash
# View test output in detail
docker compose exec backend pytest -vv

# Run specific failing test
docker compose exec backend pytest tests/test_auth.py::TestUserLogin::test_login_success -vv

# Check backend logs
docker compose logs backend
```

### Database Connection Issues

```bash
# Restart PostgreSQL
docker compose restart postgres

# Wait for health check
sleep 5

# Try tests again
docker compose exec backend pytest
```

### Permission Errors

```bash
# Fix permissions on test runner
chmod +x backend/run_tests.sh

# Or run directly with bash
docker compose exec backend bash run_tests.sh
```

## Success Criteria

✅ **All tests pass** (70/70)
✅ **Coverage is 90%+**
✅ **No errors in backend logs**
✅ **Health endpoint responds**
✅ **Can register and login users**
✅ **JWT tokens work correctly**
✅ **Database migrations applied**

## What This Verification Proves

By completing this verification, you've confirmed:

1. **Backend Infrastructure Works**
   - Docker Compose services are healthy
   - PostgreSQL database is accessible
   - FastAPI application is running

2. **Authentication System Works**
   - User registration with validation
   - Password hashing is secure
   - Login generates valid JWT tokens
   - Protected endpoints require authentication

3. **Security is Solid**
   - Passwords are hashed with bcrypt
   - JWT tokens are properly signed
   - API keys can be encrypted/decrypted
   - User isolation is maintained

4. **Database Layer Works**
   - Models are properly defined
   - Migrations are applied
   - Constraints are enforced
   - Queries work correctly

5. **Code Quality is High**
   - 90%+ test coverage
   - All edge cases handled
   - Error scenarios tested
   - Integration flows verified

## Next Steps After Verification

Once verification is complete:

1. **Commit Your Work**
   ```bash
   git add .
   git commit -m "Complete Phase 1: Backend foundation and authentication with comprehensive testing"
   ```

2. **Review Test Results**
   - Check coverage report for any gaps
   - Review test output for warnings

3. **Proceed to Phase 2**
   - Agent Management implementation
   - Agent versioning
   - Tool integration

4. **Maintain Test Coverage**
   - Add tests for new features
   - Keep coverage above 90%
   - Run tests before commits

## Need Help?

- **Test Documentation**: See [TESTING.md](./TESTING.md)
- **Detailed Test Info**: See [backend/tests/README.md](./backend/tests/README.md)
- **Implementation Details**: See [PHASE1.md](./PHASE1.md)
- **Product Spec**: See [SPEC.md](./SPEC.md)

## Quick Reference Commands

```bash
# Start everything
docker compose up -d

# Run all tests
docker compose exec backend pytest -v

# Run with coverage
docker compose exec backend pytest --cov=app --cov-report=html

# View logs
docker compose logs -f backend

# Stop everything
docker compose down

# Clean restart
docker compose down -v && docker compose up -d --build
```

---

**Congratulations!** If all tests pass, Phase 1 is complete and production-ready! 🎉
