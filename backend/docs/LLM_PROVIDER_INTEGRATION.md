# LLM Provider Integration

This document describes the LLM provider integration system in DeepAgentStudio, which allows users to securely configure and use multiple LLM providers (OpenAI, Anthropic, etc.).

## Table of Contents

- [Overview](#overview)
- [Security](#security)
- [Architecture](#architecture)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [Testing](#testing)
- [Supported Providers](#supported-providers)

## Overview

The LLM provider integration system provides:

- **Multi-provider support**: OpenAI, Anthropic, Google, Azure OpenAI, Ollama, LlamaCPP
- **Secure API key storage**: API keys are encrypted at rest using Fernet symmetric encryption
- **User isolation**: Each user manages their own provider configurations
- **Connection testing**: Verify API keys and provider configurations before use
- **Provider-specific configuration**: Each provider can have custom settings

## Security

### API Key Encryption

API keys are **never** stored in plaintext. The system uses:

1. **Fernet symmetric encryption** for encrypting API keys at rest
2. **Environment-based encryption key** (`ENCRYPTION_KEY` in settings)
3. **No API keys in responses**: API keys are never returned in API responses

```python
# API keys are encrypted before storage
encrypted_key = encrypt_api_key("sk-your-api-key")

# And decrypted only when needed
api_key = decrypt_api_key(encrypted_key)
```

### Best Practices

✅ **DO:**
- Store the `ENCRYPTION_KEY` securely (environment variables, secrets manager)
- Use a different `ENCRYPTION_KEY` for each environment (dev, staging, prod)
- Generate `ENCRYPTION_KEY` using: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- Rotate API keys regularly using the update API key endpoint

❌ **DON'T:**
- Commit `ENCRYPTION_KEY` or API keys to version control
- Share `ENCRYPTION_KEY` between environments
- Log decrypted API keys
- Return API keys in any API responses

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer                               │
│  /api/v1/llm-providers (CRUD + test connection)            │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                  Business Logic Layer                       │
│  - EncryptionService: encrypt/decrypt API keys             │
│  - LLM Clients: OpenAIClient, AnthropicClient              │
│  - Provider Management: CRUD operations                     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                   Data Layer                                │
│  - LLMProviderConfig model                                 │
│  - User relationship (CASCADE delete)                       │
│  - Encrypted API key storage                                │
└─────────────────────────────────────────────────────────────┘
```

### Database Schema

```sql
CREATE TABLE llm_provider_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider_type VARCHAR NOT NULL,  -- 'openai', 'anthropic', etc.
    name VARCHAR(255) NOT NULL,
    description TEXT,
    encrypted_api_key TEXT NOT NULL,  -- Fernet encrypted
    config JSON NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_llm_provider_configs_user_id ON llm_provider_configs(user_id);
CREATE INDEX idx_llm_provider_configs_provider_type ON llm_provider_configs(provider_type);
```

## API Endpoints

All endpoints require authentication via JWT token.

### Create Provider Configuration

```http
POST /api/v1/llm-providers
Authorization: Bearer <token>
Content-Type: application/json

{
  "provider_type": "openai",
  "name": "My OpenAI Config",
  "description": "Production OpenAI configuration",
  "api_key": "sk-your-api-key-here",
  "config": {
    "organization_id": "org-123",
    "default_model": "gpt-4",
    "timeout": 60
  }
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "user_id": 1,
  "provider_type": "openai",
  "name": "My OpenAI Config",
  "description": "Production OpenAI configuration",
  "config": {
    "organization_id": "org-123",
    "default_model": "gpt-4",
    "timeout": 60
  },
  "is_active": true,
  "has_api_key": true,
  "last_used_at": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Note:** The API key is NOT included in the response.

### List Provider Configurations

```http
GET /api/v1/llm-providers?skip=0&limit=50&active_only=false
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "providers": [
    {
      "id": 1,
      "provider_type": "openai",
      "name": "My OpenAI Config",
      "has_api_key": true,
      ...
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 50
}
```

### Get Provider Configuration

```http
GET /api/v1/llm-providers/{provider_id}
Authorization: Bearer <token>
```

**Response:** `200 OK` (same structure as create response)

### Update Provider Configuration

```http
PUT /api/v1/llm-providers/{provider_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Updated Name",
  "description": "Updated description",
  "config": {
    "default_model": "gpt-4-turbo"
  },
  "is_active": true
}
```

**Note:** This endpoint CANNOT update the API key. Use the separate API key update endpoint.

### Update API Key

```http
PUT /api/v1/llm-providers/{provider_id}/api-key
Authorization: Bearer <token>
Content-Type: application/json

{
  "api_key": "sk-new-api-key-here"
}
```

**Response:** `200 OK` (provider config, key NOT included)

This is a separate endpoint for security - API keys should only be updated when explicitly intended.

### Delete Provider Configuration

```http
DELETE /api/v1/llm-providers/{provider_id}
Authorization: Bearer <token>
```

**Response:** `204 No Content`

### Test Provider Connection

```http
POST /api/v1/llm-providers/{provider_id}/test
Authorization: Bearer <token>
Content-Type: application/json

{
  "test_message": "Hello, this is a test."
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "response": "Hello! How can I help you today?",
  "latency_ms": 847,
  "tokens_used": 21,
  "error": null
}
```

Or on failure:
```json
{
  "success": false,
  "response": null,
  "latency_ms": null,
  "tokens_used": null,
  "error": "Authentication failed: Invalid API key"
}
```

**⚠️ Warning:** This makes a real API call and will incur costs (minimal, ~$0.001).

## Usage Examples

### Python Client Example

```python
import httpx

# Authenticate
response = httpx.post("http://localhost:8000/api/v1/auth/login", data={
    "username": "user",
    "password": "password"
})
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Create OpenAI provider
openai_config = {
    "provider_type": "openai",
    "name": "Production OpenAI",
    "api_key": "sk-your-openai-key",
    "config": {
        "default_model": "gpt-4",
        "timeout": 60
    }
}

response = httpx.post(
    "http://localhost:8000/api/v1/llm-providers",
    json=openai_config,
    headers=headers
)
provider = response.json()
print(f"Created provider: {provider['id']}")

# Test connection
test_response = httpx.post(
    f"http://localhost:8000/api/v1/llm-providers/{provider['id']}/test",
    headers=headers
)
test_result = test_response.json()
print(f"Connection test: {'✓ Success' if test_result['success'] else '✗ Failed'}")
```

### JavaScript/TypeScript Example

```typescript
// Authenticate
const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({
    username: 'user',
    password: 'password'
  })
});
const { access_token } = await loginResponse.json();

// Create Anthropic provider
const anthropicConfig = {
  provider_type: 'anthropic',
  name: 'Production Claude',
  api_key: 'sk-ant-your-anthropic-key',
  config: {
    default_model: 'claude-3-5-sonnet-20241022',
    timeout: 60
  }
};

const createResponse = await fetch('http://localhost:8000/api/v1/llm-providers', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(anthropicConfig)
});

const provider = await createResponse.json();
console.log('Created provider:', provider.id);

// List all providers
const listResponse = await fetch('http://localhost:8000/api/v1/llm-providers', {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
const { providers } = await listResponse.json();
console.log(`You have ${providers.length} providers configured`);
```

## Testing

### Unit Tests (Mocked)

Unit tests use mocked API responses and don't make real API calls:

```bash
# Run all LLM-related unit tests
docker-compose exec backend pytest tests/test_llm_clients.py -v
docker-compose exec backend pytest tests/test_llm_provider_api.py -v
docker-compose exec backend pytest tests/test_llm_provider_models.py -v

# Run all tests
docker-compose exec backend pytest tests/ -v
```

**Test Coverage:**
- ✅ 18 client tests (OpenAI, Anthropic)
- ✅ 27 API endpoint tests
- ✅ 15 model/database tests
- ✅ **Total: 60 tests, all passing**

### Integration Tests (Real APIs)

Optional integration tests make real API calls:

```bash
# Set API keys
export OPENAI_API_KEY="sk-your-key"
export ANTHROPIC_API_KEY="sk-ant-your-key"

# Run integration tests
docker-compose exec backend pytest tests/test_llm_integration.py -m integration -v

# Run specific provider tests
docker-compose exec backend pytest tests/test_llm_integration.py::TestOpenAIIntegration -m integration -v
```

**⚠️ Warning:** Integration tests make real API calls and will incur small costs (~$0.05 per full run).

## Supported Providers

### OpenAI

**Provider Type:** `openai`

**Configuration:**
```json
{
  "organization_id": "org-123",  // Optional
  "default_model": "gpt-4",      // Default model
  "timeout": 60                  // Request timeout in seconds
}
```

**Supported Models:**
- `gpt-4`
- `gpt-4-turbo`
- `gpt-3.5-turbo`
- Others as available from OpenAI

**API Key Format:** `sk-...`

**Documentation:** https://platform.openai.com/docs/api-reference

### Anthropic

**Provider Type:** `anthropic`

**Configuration:**
```json
{
  "default_model": "claude-3-5-sonnet-20241022",
  "timeout": 60
}
```

**Supported Models:**
- `claude-3-5-sonnet-20241022`
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`
- `claude-3-haiku-20240307`

**API Key Format:** `sk-ant-...`

**Documentation:** https://docs.anthropic.com/claude/reference/

### Google (Coming Soon)

**Provider Type:** `google`

Support for Google's Gemini models is planned.

### Azure OpenAI (Coming Soon)

**Provider Type:** `azure_openai`

Support for Azure-hosted OpenAI models is planned.

### Local Providers

**Ollama:** `ollama` - For locally-hosted models
**LlamaCPP:** `llamacpp` - For llama.cpp models

## Error Handling

The LLM clients provide specific exception types:

```python
from app.llm.base import (
    LLMAuthenticationError,    # Invalid API key (401)
    LLMRateLimitError,         # Rate limit exceeded (429)
    LLMInvalidRequestError,    # Bad request (400)
    LLMConnectionError,        # Network/timeout errors
)

try:
    response = await client.generate(messages=[...])
except LLMAuthenticationError:
    # Handle invalid API key
    print("API key is invalid")
except LLMRateLimitError:
    # Handle rate limiting
    print("Rate limit exceeded, try again later")
except LLMConnectionError:
    # Handle network errors
    print("Connection failed")
```

## Migration Guide

If you're upgrading from a system without provider management:

1. **Backup existing API keys** from environment variables
2. **Run database migration**: `alembic upgrade head`
3. **Create provider configurations** via API for each user
4. **Update agent configurations** to reference provider configs
5. **Remove hardcoded API keys** from environment

## Troubleshooting

### Common Issues

**Issue:** "AttributeError: 'Settings' object has no attribute 'ENCRYPTION_KEY'"
**Solution:** Ensure `ENCRYPTION_KEY` is set in environment variables or .env file.

**Issue:** "Invalid encrypted API key"
**Solution:** The `ENCRYPTION_KEY` changed. You'll need to re-create provider configs with new API keys.

**Issue:** "Authentication failed" during connection test
**Solution:** Verify the API key is correct and active on the provider's dashboard.

**Issue:** Tests failing with "OPENAI_API_KEY environment variable not set"
**Solution:** Integration tests are optional. Either set the env var or skip with `pytest -m "not integration"`.

## Security Checklist

Before deploying to production:

- [ ] Generate a new, unique `ENCRYPTION_KEY` for production
- [ ] Store `ENCRYPTION_KEY` in a secure secrets manager
- [ ] Enable HTTPS for all API communications
- [ ] Implement rate limiting on API endpoints
- [ ] Set up monitoring for failed authentication attempts
- [ ] Regular audit of API key usage
- [ ] Implement API key rotation policy
- [ ] Ensure database backups are encrypted
- [ ] Review CORS settings for production domains

## Contributing

When adding a new LLM provider:

1. Implement `BaseLLMClient` interface in `app/llm/<provider>_client.py`
2. Add provider type to `LLMProviderType` enum
3. Create provider-specific config schema in `app/schemas/llm_provider.py`
4. Add factory function in the API endpoint test handler
5. Write unit tests with mocked responses
6. Write optional integration tests
7. Update this documentation

## License

See the main project LICENSE file.
