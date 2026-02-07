# OpenAI-Compatible Provider Type

## Problem

Users want to connect to any OpenAI API-compliant server (vLLM, LM Studio, Ollama, llama.cpp, Together AI, Groq, OpenRouter, etc.) and use available models in their agents. Currently they must use the "OpenAI" provider type with a custom base_url, which is confusing and carries OpenAI-specific parameter quirks (max_completion_tokens, ChatOpenAINoStop wrapper) that break with other servers.

## Solution

Add a dedicated `openai_compatible` provider type with:
- Required base URL, optional API key
- Model auto-discovery via `GET /v1/models`
- Clean parameter handling (standard `max_tokens`, no OpenAI-specific quirks)

## Design

### 1. Provider Type & Config Schema

New enum value: `openai_compatible`

Backend config schema (`OpenAICompatibleConfig`):
- `base_url: str` — Required
- `default_model: Optional[str]` — Last selected model
- `max_tokens: Optional[int]` — Default 1024
- `temperature: Optional[float]` — Default 0.7

Key differences from `OpenAIConfig`:
- `base_url` is required (not optional)
- No `organization_id`
- No `max_completion_tokens` logic — always plain `max_tokens`
- API key optional at schema level

### 2. Model Discovery Endpoint

```
POST /api/v1/llm-providers/discover-models
Body: { base_url: string, api_key?: string }
Response: { success: bool, models: string[], error?: string }
```

- Calls `GET {base_url}/models` (standard OpenAI-compatible endpoint)
- 10-second timeout
- Works before provider is saved (during initial setup)
- Requires JWT authentication

### 3. LLM Adapter

New `_create_openai_compatible()` method in `LLMProviderAdapter`:
- Creates standard `ChatOpenAI` with base_url, model, temperature, max_tokens
- API key defaults to `"not-needed"` if empty (LangChain requires non-empty string)
- No `ChatOpenAINoStop` wrapper
- No `max_completion_tokens` conversion
- Defaults to attempting tool calling

### 4. Frontend Form

When `openai_compatible` is selected:
1. **Name** — text field
2. **Base URL** — required, placeholder `http://localhost:8000/v1`
3. **API Key** — optional, with hint: "Required for cloud services, not needed for most local servers"
4. **Model** — combobox + "Fetch Models" button for auto-discovery, accepts manual entry
5. **Advanced** — temperature, max_tokens defaults

No predefined models list. No custom models editor. Models come from discovery or manual entry.

### 5. Files Changed

**Backend:**
- `backend/app/models/llm_provider.py` — add enum value
- `backend/app/schemas/llm_provider.py` — add config class
- `backend/app/api/v1/llm_providers.py` — add discover-models endpoint
- `backend/app/llm/openai_client.py` — no changes needed (reuses ChatOpenAI)
- `backend/app/services/llm_adapter.py` — add `_create_openai_compatible()`
- `backend/app/services/agent_executor.py` — update `supports_tool_calling()`

**Frontend:**
- `frontend/src/api/types.ts` — add type, add discover request/response
- `frontend/src/config/llmProviders.ts` — add provider config entry
- `frontend/src/components/settings/LLMProviderForm.tsx` — add form variant with model discovery
- `frontend/src/api/hooks/` — add useDiscoverModels hook

**Database:**
- Alembic migration to add `openai_compatible` to provider_type enum
