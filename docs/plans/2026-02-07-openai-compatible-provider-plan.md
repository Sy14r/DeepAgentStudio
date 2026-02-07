# OpenAI-Compatible Provider Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a dedicated `openai_compatible` provider type so users can connect to any OpenAI API-compliant server and use its models in their agents.

**Architecture:** New enum value + config schema on backend, model discovery endpoint, LLM adapter method, and frontend form with auto-discovery UI. Reuses LangChain's `ChatOpenAI` under the hood since it already supports custom base URLs.

**Tech Stack:** Python/FastAPI, SQLAlchemy, LangChain, Alembic, React/TypeScript, TanStack Query, shadcn/ui

---

### Task 1: Backend — Add enum value to models and schemas

**Files:**
- Modify: `backend/app/models/llm_provider.py:14-21`
- Modify: `backend/app/schemas/llm_provider.py:14-21`
- Modify: `backend/app/schemas/llm_provider.py:97-133` (add new config class)

**Step 1: Add OPENAI_COMPATIBLE to model enum**

In `backend/app/models/llm_provider.py`, add to `LLMProviderType`:
```python
class LLMProviderType(str, Enum):
    """LLM provider types"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"
    OPENAI_COMPATIBLE = "openai_compatible"
```

**Step 2: Add openai_compatible to schema enum**

In `backend/app/schemas/llm_provider.py`, add to `LLMProviderType`:
```python
class LLMProviderType(str, Enum):
    """LLM provider types"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"
    OPENAI_COMPATIBLE = "openai_compatible"
```

**Step 3: Add OpenAICompatibleConfig class**

In `backend/app/schemas/llm_provider.py`, after `OllamaConfig`, add:
```python
class OpenAICompatibleConfig(BaseModel):
    """Configuration for OpenAI API-compatible servers (vLLM, LM Studio, llama.cpp, etc.)"""
    base_url: str = Field(..., description="Base URL of the OpenAI-compatible server (required)")
    default_model: Optional[str] = Field(None, description="Default model to use")
    max_tokens: Optional[int] = Field(None, ge=1, le=128000, description="Max tokens")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperature")
```

---

### Task 2: Backend — Add model discovery endpoint

**Files:**
- Modify: `backend/app/api/v1/llm_providers.py:1-34` (add imports)
- Modify: `backend/app/api/v1/llm_providers.py` (add new endpoint after line 34)
- Modify: `backend/app/schemas/llm_provider.py` (add request/response schemas)

**Step 1: Add discovery schemas**

In `backend/app/schemas/llm_provider.py`, add after `LLMProviderTestResponse`:
```python
class DiscoverModelsRequest(BaseModel):
    """Schema for discovering models from an OpenAI-compatible server"""
    base_url: str = Field(..., description="Base URL of the server")
    api_key: Optional[str] = Field(None, description="Optional API key")

class DiscoverModelsResponse(BaseModel):
    """Schema for model discovery response"""
    success: bool = Field(..., description="Whether discovery succeeded")
    models: list[str] = Field(default_factory=list, description="List of model IDs")
    error: Optional[str] = Field(None, description="Error message if failed")
```

**Step 2: Add discover-models endpoint**

In `backend/app/api/v1/llm_providers.py`, add imports for `httpx` and the new schemas, then add the endpoint before the CRUD routes (after `router = APIRouter()`):

```python
import httpx

# Add to imports from schemas:
from ...schemas.llm_provider import (
    ...,
    DiscoverModelsRequest,
    DiscoverModelsResponse,
)

@router.post("/discover-models", response_model=DiscoverModelsResponse)
async def discover_models(
    request: DiscoverModelsRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Discover available models from an OpenAI-compatible server.

    Calls GET {base_url}/models to list available models.
    Works before a provider is saved (during initial setup).
    """
    try:
        # Normalize base URL
        base_url = request.base_url.rstrip("/")

        # Build headers
        headers = {}
        if request.api_key:
            headers["Authorization"] = f"Bearer {request.api_key}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/models", headers=headers)
            response.raise_for_status()

        data = response.json()
        # OpenAI-compatible format: {"data": [{"id": "model-name", ...}, ...]}
        models = []
        if isinstance(data, dict) and "data" in data:
            models = [m["id"] for m in data["data"] if isinstance(m, dict) and "id" in m]
        elif isinstance(data, list):
            models = [m["id"] for m in data if isinstance(m, dict) and "id" in m]

        models.sort()
        return DiscoverModelsResponse(success=True, models=models)

    except httpx.TimeoutException:
        return DiscoverModelsResponse(
            success=False,
            error="Connection timed out. Is the server running?"
        )
    except httpx.HTTPStatusError as e:
        return DiscoverModelsResponse(
            success=False,
            error=f"Server returned {e.response.status_code}: {e.response.text[:200]}"
        )
    except Exception as e:
        return DiscoverModelsResponse(
            success=False,
            error=f"Failed to connect: {str(e)}"
        )
```

**Step 3: Update test endpoint to handle openai_compatible**

In `backend/app/api/v1/llm_providers.py`, update the `test_provider_connection` function's provider type check to handle `openai_compatible`:

```python
        if provider.provider_type in ("openai", "openai_compatible"):
            client = create_openai_client(api_key, provider.config)
```

---

### Task 3: Backend — Add LLM adapter method

**Files:**
- Modify: `backend/app/services/llm_adapter.py:183-212` (add new elif branch)
- Modify: `backend/app/services/llm_adapter.py:373-393` (update supported providers)

**Step 1: Add _create_openai_compatible static method**

In `backend/app/services/llm_adapter.py`, add after `_create_anthropic` method (after line 370):

```python
    @staticmethod
    def _create_openai_compatible(api_key: str, config: Dict[str, Any]) -> ChatOpenAI:
        """
        Create LLM for OpenAI API-compatible servers.

        Unlike _create_openai, this method:
        - Always uses max_tokens (no max_completion_tokens conversion)
        - Does not use the ChatOpenAINoStop wrapper
        - Requires base_url in config

        Args:
            api_key: API key (may be "not-required" for local servers)
            config: Configuration dict with base_url, model, temperature, etc.

        Returns:
            ChatOpenAI instance configured for the compatible server
        """
        base_url = config.get("base_url")
        if not base_url:
            raise LLMAdapterError("base_url is required for openai_compatible provider")

        model = config.get("model") or config.get("default_model", "")
        if not model:
            raise LLMAdapterError("model is required for openai_compatible provider")

        temperature = config.get("temperature", 0.7)
        max_tokens = config.get("max_tokens")
        timeout = config.get("timeout", 60)

        kwargs = {
            "api_key": api_key if api_key != "not-required" else "not-needed",
            "base_url": base_url,
            "model": model,
            "temperature": temperature,
            "timeout": timeout,
            "stream_usage": True,
        }

        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        logger.debug(f"Creating OpenAI-compatible LLM: base_url={base_url}, model={model}, temp={temperature}")

        return ChatOpenAI(**kwargs)
```

**Step 2: Add elif branch in create_llm**

In `backend/app/services/llm_adapter.py`, add after the OLLAMA elif block (around line 202):

```python
        elif provider_type == LLMProviderType.OPENAI_COMPATIBLE:
            return LLMProviderAdapter._create_openai_compatible(api_key, merged_config)
```

**Step 3: Update supported providers list**

In `get_supported_providers()`:
```python
        return ["openai", "anthropic", "openai_compatible"]
```

---

### Task 4: Backend — Update agent executor for tool calling

**Files:**
- Modify: `backend/app/services/agent_executor.py:158-187`

**Step 1: Update supports_tool_calling function**

In `backend/app/services/agent_executor.py`, add a check for `openai_compatible` provider. Since we can't know which models support tool calling on arbitrary servers, we default to True (attempt tool calling):

Add at the end of `supports_tool_calling()`, before the final `return False`:
```python
    # For openai_compatible providers, default to attempting tool calling
    # Most modern inference servers support it
    # This is checked separately using provider_type context
    return False
```

This function only checks model names, so no change is needed here. The tool calling will naturally work because `ChatOpenAI` supports it natively — LangChain handles the protocol.

---

### Task 5: Backend — Add database migration

**Files:**
- Create: `backend/alembic/versions/o5p6q7r8s9t0_add_openai_compatible_provider_type.py`

**Step 1: Create migration file**

```python
"""add_openai_compatible_provider_type

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-02-07

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'o5p6q7r8s9t0'
down_revision: Union[str, None] = 'n4o5p6q7r8s9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE llmprovidertype ADD VALUE IF NOT EXISTS 'OPENAI_COMPATIBLE'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values
    # The value will remain but be unused after downgrade
    pass
```

**Step 2: Run migration**

```bash
docker-compose exec backend alembic upgrade head
```

---

### Task 6: Backend — Add httpx dependency

**Files:**
- Modify: `backend/requirements.txt` (or pyproject.toml)

**Step 1: Check if httpx is already available**

```bash
docker-compose exec backend pip list | grep httpx
```

httpx is typically available as a transitive dependency of FastAPI/Starlette, but verify. If not present:

```bash
docker-compose exec backend pip install httpx
```

Add to requirements.txt if needed.

---

### Task 7: Frontend — Update TypeScript types

**Files:**
- Modify: `frontend/src/api/types.ts:384` (add to LLMProviderType)
- Modify: `frontend/src/api/types.ts` (add discover models types)

**Step 1: Add openai_compatible to LLMProviderType**

```typescript
export type LLMProviderType = 'openai' | 'anthropic' | 'google' | 'azure_openai' | 'ollama' | 'llamacpp' | 'openai_compatible';
```

**Step 2: Add discover models types**

After `LLMProviderConfig` interface:
```typescript
export interface DiscoverModelsRequest {
  base_url: string;
  api_key?: string;
}

export interface DiscoverModelsResponse {
  success: boolean;
  models: string[];
  error?: string;
}
```

---

### Task 8: Frontend — Add provider config entry

**Files:**
- Modify: `frontend/src/config/llmProviders.ts:41-345` (add openai_compatible entry)

**Step 1: Add openai_compatible to LLM_PROVIDER_CONFIG**

After the `llamacpp` entry:
```typescript
  openai_compatible: {
    name: 'OpenAI-Compatible',
    models: [],  // Models come from auto-discovery or manual entry
    parameters: {
      temperature: {
        min: 0,
        max: 2,
        default: 0.7,
        step: 0.1,
        description: 'Controls randomness. Lower = more focused, higher = more creative.',
      },
      max_tokens: {
        min: 1,
        max: 32768,
        default: 4096,
        step: 1,
        description: 'Maximum tokens to generate in the response.',
      },
      top_p: {
        min: 0,
        max: 1,
        default: 1,
        step: 0.05,
        optional: true,
        description: 'Nucleus sampling threshold.',
      },
    },
    notes: [
      'Connect to any OpenAI API-compatible server',
      'Supports vLLM, LM Studio, llama.cpp, Ollama, Together AI, Groq, OpenRouter, and more',
      'Use "Fetch Models" to auto-discover available models from your server',
    ],
  },
```

---

### Task 9: Frontend — Add useDiscoverModels hook

**Files:**
- Modify: `frontend/src/api/hooks/useLLMProviders.ts` (add hook)
- Modify: `frontend/src/api/hooks/index.ts` (export hook)

**Step 1: Add useDiscoverModels hook**

In `frontend/src/api/hooks/useLLMProviders.ts`:
```typescript
import { ..., DiscoverModelsRequest, DiscoverModelsResponse } from '@/api/types';

export function useDiscoverModels() {
  return useMutation({
    mutationFn: async (data: DiscoverModelsRequest): Promise<DiscoverModelsResponse> => {
      const response = await apiClient.post<DiscoverModelsResponse>('/llm-providers/discover-models', data);
      return response.data;
    },
  });
}
```

**Step 2: Export from index**

In `frontend/src/api/hooks/index.ts`, add `useDiscoverModels` to the useLLMProviders export list.

---

### Task 10: Frontend — Update LLMProviderForm with model discovery

**Files:**
- Modify: `frontend/src/components/settings/LLMProviderForm.tsx`

**Step 1: Update PROVIDER_TYPES array**

Add the new provider type:
```typescript
  { value: 'openai_compatible', label: 'OpenAI-Compatible', description: 'vLLM, LM Studio, Ollama, llama.cpp, Groq, and more' },
```

**Step 2: Update form schema**

Add `openai_compatible` to the provider_type enum:
```typescript
const providerFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be less than 100 characters'),
  provider_type: z.enum(['openai', 'anthropic', 'google', 'azure_openai', 'ollama', 'llamacpp', 'openai_compatible']),
  api_key: z.string().optional(),
  base_url: z.string().optional(),
});
```

**Step 3: Update needsBaseUrl and isApiKeyOptional logic**

```typescript
const needsBaseUrl = ['openai', 'azure_openai', 'ollama', 'llamacpp', 'openai_compatible'].includes(selectedProviderType);
const isLocalProvider = ['ollama', 'llamacpp', 'openai_compatible'].includes(selectedProviderType);
const isApiKeyOptional = isLocalProvider || (selectedProviderType === 'openai' && !!baseUrlValue?.trim());
```

**Step 4: Add model discovery state and UI**

Add imports and state:
```typescript
import { useDiscoverModels } from '@/api/hooks';
import { RefreshCw } from 'lucide-react';

// Inside component:
const [discoveredModels, setDiscoveredModels] = useState<string[]>([]);
const discoverModels = useDiscoverModels();
```

Add model discovery section in the form (after base URL field, when provider is `openai_compatible`):
```tsx
{selectedProviderType === 'openai_compatible' && (
  <div className="space-y-2">
    <FormLabel>Model</FormLabel>
    <div className="flex gap-2">
      <Input
        placeholder="Enter model name or fetch from server"
        value={form.watch('base_url') ? '' : ''}
        // This will be a controlled combobox - see full implementation
      />
      <Button
        type="button"
        variant="outline"
        size="sm"
        disabled={!baseUrlValue?.trim() || discoverModels.isPending}
        onClick={() => {
          discoverModels.mutate(
            { base_url: baseUrlValue!, api_key: form.getValues('api_key') || undefined },
            { onSuccess: (data) => { if (data.success) setDiscoveredModels(data.models); } }
          );
        }}
      >
        {discoverModels.isPending ? <Spinner className="h-4 w-4" /> : <RefreshCw className="h-4 w-4" />}
        Fetch Models
      </Button>
    </div>
    {discoveredModels.length > 0 && (
      <div className="max-h-40 overflow-y-auto border rounded-md">
        {discoveredModels.map(model => (
          <button key={model} type="button" className="..." onClick={() => { /* select model */ }}>
            {model}
          </button>
        ))}
      </div>
    )}
  </div>
)}
```

**Step 5: Update API key hint for openai_compatible**

When provider is `openai_compatible`, show:
```
"Required for cloud services (Together AI, Groq, OpenRouter). Not needed for most local servers."
```

---

### Task 11: Build, test, and verify

**Step 1: Rebuild containers**

```bash
docker-compose up -d --build
```

**Step 2: Run migration**

```bash
docker-compose exec backend alembic upgrade head
```

**Step 3: Run backend tests**

```bash
docker-compose exec -T backend pytest -v
```

**Step 4: Run frontend build**

```bash
docker-compose exec -T frontend npm run build
```

**Step 5: Run frontend lint**

```bash
docker-compose exec -T frontend npm run lint
```

**Step 6: Manual verification**

1. Open the app, go to Settings > LLM Providers
2. Click "Add Provider" and select "OpenAI-Compatible"
3. Verify base URL is required, API key is optional
4. If you have a local server running, test model discovery
5. Create the provider and verify it appears in the list
6. Create/edit an agent and verify the new provider is available
7. Test provider connection via the test button

---

### Task 12: Commit

```bash
git add -A
git commit -m "feat: add OpenAI-compatible provider type with model auto-discovery

Adds a dedicated 'openai_compatible' provider type for connecting to any
OpenAI API-compliant server (vLLM, LM Studio, llama.cpp, Ollama, Together AI,
Groq, OpenRouter, etc.).

- New provider type with required base_url, optional API key
- Model auto-discovery endpoint (POST /llm-providers/discover-models)
- Clean parameter handling (standard max_tokens, no OpenAI quirks)
- Frontend form with Fetch Models button and manual entry fallback
- Database migration to add enum value

Generated with [Claude Code](https://claude.ai/code)
via [Happy](https://happy.engineering)

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Happy <yesreply@happy.engineering>"
```
