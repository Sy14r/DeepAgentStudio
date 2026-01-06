# DeepAgentStudio - Phase 1: Backend Foundation

## Overview
**Duration**: Week 1
**Goal**: Set up backend infrastructure, authentication, and database foundation
**Approach**: Backend-first development

---

## Phase 1: Project Setup

### Objective
Initialize FastAPI project with proper organization and Docker infrastructure

### Directory Structure to Create
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── security.py
│   ├── dependencies.py
│   ├── models/
│   │   └── __init__.py
│   ├── schemas/
│   │   └── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   └── utils/
│       ├── __init__.py
│       └── encryption.py
├── alembic/
├── tests/
│   └── __init__.py
├── requirements.txt
├── requirements-dev.txt
├── alembic.ini
├── Dockerfile
└── .env.example
```

### Files to Create

#### 1. backend/requirements.txt
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9
pydantic==2.5.3
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
langchain==0.1.0
langchain-openai==0.0.2
langchain-anthropic==0.0.1
langchain-community==0.0.10
cryptography==41.0.7
python-dotenv==1.0.0
duckduckgo-search==4.1.1
wikipedia==1.4.0
```

#### 2. backend/requirements-dev.txt
```
pytest==7.4.4
pytest-asyncio==0.23.3
httpx==0.26.0
black==24.1.1
flake8==7.0.0
mypy==1.8.0
```

#### 3. backend/app/config.py
**Purpose**: Centralized configuration using Pydantic settings

**Key Content**:
- Database URL (from environment)
- JWT secret key and algorithm
- API key encryption settings
- CORS settings
- Environment mode (dev/prod)

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Encryption
    ENCRYPTION_KEY: str

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Environment
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()
```

#### 4. backend/app/database.py
**Purpose**: SQLAlchemy database connection and session management

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### 5. backend/app/security.py
**Purpose**: Authentication and encryption utilities

**Key Functions**:
```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    """Decode JWT access token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

# Dependency for getting current user (will be implemented with User model)
```

#### 6. backend/app/utils/encryption.py
**Purpose**: API key encryption/decryption for secure storage

```python
from cryptography.fernet import Fernet
from ..config import settings

def get_fernet() -> Fernet:
    """Get Fernet cipher instance"""
    return Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt_api_key(api_key: str) -> str:
    """Encrypt API key for storage"""
    if not api_key:
        return None
    fernet = get_fernet()
    return fernet.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key from storage"""
    if not encrypted_key:
        return None
    fernet = get_fernet()
    return fernet.decrypt(encrypted_key.encode()).decode()
```

#### 7. backend/.env.example
**Purpose**: Environment variable template

```env
# Database
DATABASE_URL=postgresql://deepagent:deepagent@postgres:5432/deepagentstudio

# JWT
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Encryption (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your-fernet-encryption-key-change-this-in-production

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Environment
ENVIRONMENT=development
```

#### 8. docker-compose.yml (Project Root)
**Purpose**: Multi-service orchestration for local development

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: deepagent_postgres
    environment:
      POSTGRES_USER: deepagent
      POSTGRES_PASSWORD: deepagent
      POSTGRES_DB: deepagentstudio
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U deepagent"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: deepagent_backend
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      DATABASE_URL: postgresql://deepagent:deepagent@postgres:5432/deepagentstudio
      JWT_SECRET_KEY: dev-secret-key-change-in-production
      JWT_ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 30
      ENCRYPTION_KEY: dev-encryption-key-change-in-production
      CORS_ORIGINS: http://localhost:5173,http://localhost:3000
      ENVIRONMENT: development
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
```

#### 9. backend/Dockerfile
**Purpose**: Backend container definition

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Command will be overridden by docker-compose
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 10. backend/app/main.py
**Purpose**: FastAPI application entry point

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings

app = FastAPI(
    title="DeepAgentStudio API",
    description="API for managing LangChain deepagents",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "DeepAgentStudio API", "version": "0.1.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# API routers will be included here
# from .api.v1 import auth, agents, tools, prompts, sessions
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
```

### Actions After File Creation

1. **Generate Encryption Key**:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. **Initialize Alembic**:
   ```bash
   cd backend
   alembic init alembic
   ```

3. **Configure alembic.ini**:
   - Update `sqlalchemy.url` to use environment variable or direct connection string

4. **Configure alembic/env.py**:
   - Import models Base
   - Set target_metadata to Base.metadata

5. **Test Docker Compose**:
   ```bash
   docker-compose up -d
   docker-compose logs -f backend
   ```

6. **Verify API**:
   - Visit http://localhost:8000
   - Visit http://localhost:8000/docs (OpenAPI documentation)

---

## Phase 2: Authentication

### Objective
Implement user authentication with JWT tokens

### Files to Create

#### 1. backend/app/models/user.py
**Purpose**: User SQLAlchemy model

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships (to be added later)
    # agents = relationship("Agent", back_populates="user")
    # prompts = relationship("Prompt", back_populates="user")
    # sessions = relationship("Session", back_populates="user")
```

#### 2. backend/app/schemas/user.py
**Purpose**: Pydantic schemas for user data validation

```python
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
```

#### 3. backend/app/api/deps.py
**Purpose**: Shared API dependencies

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from ..database import get_db
from ..security import decode_access_token
from ..models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
```

#### 4. backend/app/api/v1/auth.py
**Purpose**: Authentication API endpoints

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from ...database import get_db
from ...security import hash_password, verify_password, create_access_token
from ...models.user import User
from ...schemas.user import UserCreate, UserResponse, Token
from ...config import settings
from ..deps import get_current_active_user

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if username exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = hash_password(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and get access token"""
    # Find user
    user = db.query(User).filter(User.username == form_data.username).first()

    # Verify credentials
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user
```

#### 5. Update backend/app/main.py
Add authentication router:

```python
from .api.v1 import auth

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
```

### Database Migration

#### Create Initial Migration
```bash
cd backend
alembic revision --autogenerate -m "create users table"
```

#### Review Migration
Check the generated file in `alembic/versions/` to ensure it correctly creates:
- users table with all columns
- unique constraints on username and email
- indexes on username and email

#### Apply Migration
```bash
alembic upgrade head
```

### Testing

#### 1. Start Services
```bash
docker-compose up -d
docker-compose logs -f backend
```

#### 2. Test Endpoints

**Register User**:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpassword123"
  }'
```

**Login**:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpassword123"
```

**Get Current User**:
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <access_token_from_login>"
```

#### 3. Verify in Database
```bash
docker-compose exec postgres psql -U deepagent -d deepagentstudio
SELECT * FROM users;
```

### Automated Tests

#### backend/tests/conftest.py
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

#### backend/tests/test_auth.py
```python
def test_register_user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data

def test_register_duplicate_username(client):
    # First registration
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test1@example.com",
            "password": "testpassword123"
        }
    )

    # Duplicate username
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test2@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 400

def test_login(client):
    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )

    # Login
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_get_current_user(client):
    # Register and login
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpassword123"
        }
    )
    token = login_response.json()["access_token"]

    # Get current user
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
```

#### Run Tests
```bash
cd backend
pytest -v
```

---

## Success Criteria for Phase 1

- ✅ Docker Compose runs successfully with PostgreSQL and backend
- ✅ Backend API accessible at http://localhost:8000
- ✅ OpenAPI docs accessible at http://localhost:8000/docs
- ✅ User registration works
- ✅ User login returns JWT token
- ✅ Protected endpoint (/me) requires valid token
- ✅ All automated tests pass
- ✅ Database migrations work correctly

---

## Next Steps

After completing Phase 1, proceed to:
- **Phase 3**: Agent CRUD (Week 2)
- **Phase 4**: Tool Management (Week 3)
- **Phase 5**: Prompt Management (Week 3)
- **Phase 6**: Agent Execution (Week 4)

---

## Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps

# View PostgreSQL logs
docker-compose logs postgres

# Connect to PostgreSQL manually
docker-compose exec postgres psql -U deepagent -d deepagentstudio
```

### Alembic Migration Issues
```bash
# Check current revision
alembic current

# View migration history
alembic history

# Downgrade if needed
alembic downgrade -1
```

### Backend Errors
```bash
# View backend logs
docker-compose logs -f backend

# Restart backend
docker-compose restart backend

# Rebuild backend
docker-compose up -d --build backend
```

---

**End of Phase 1 Documentation**
