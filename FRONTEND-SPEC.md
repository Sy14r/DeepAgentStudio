# DeepAgentStudio Frontend Specification

**Created**: 2026-01-03
**Status**: Planning

## 1. Overview

This document outlines the implementation plan for the DeepAgentStudio frontend - a React-based web application for building, managing, and interacting with LangChain agents.

### Goals
- Provide intuitive UI for all backend functionality
- Enable real-time agent interaction via chat interface
- Display execution traces and observability data
- Support agent, tool, and prompt management with versioning

### Backend API
The backend is complete with 54+ REST endpoints:
- `POST /api/v1/auth/*` - Authentication
- `GET/POST/PUT/DELETE /api/v1/agents/*` - Agent management + `/invoke`
- `GET/POST/PUT/DELETE /api/v1/tools/*` - Tool management
- `GET/POST/PUT/DELETE /api/v1/prompts/*` - Prompt management
- `GET/POST/PUT/DELETE /api/v1/sessions/*` - Session & trace management
- `GET/POST/PUT/DELETE /api/v1/llm-providers/*` - LLM provider configuration

API Documentation: http://localhost:8000/docs

---

## 2. Technology Stack

### Core
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.x | UI Framework |
| TypeScript | 5.x | Type safety |
| Vite | 5.x | Build tool & dev server |
| React Router | 6.x | Client-side routing |

### UI & Styling
| Technology | Purpose |
|------------|---------|
| shadcn/ui | Component library (built on Radix UI) |
| Tailwind CSS | Utility-first styling |
| Lucide React | Icons |
| Framer Motion | Animations (optional) |

### State & Data
| Technology | Purpose |
|------------|---------|
| Zustand | Global state management |
| TanStack Query | Server state, caching, mutations |
| React Hook Form | Form handling |
| Zod | Schema validation |

### Code Editing
| Technology | Purpose |
|------------|---------|
| Monaco Editor | Code editing for tools/prompts |
| react-markdown | Markdown rendering in chat |
| Prism/Shiki | Syntax highlighting |

### Development
| Technology | Purpose |
|------------|---------|
| ESLint | Linting |
| Prettier | Code formatting |
| Vitest | Unit testing |
| Playwright | E2E testing (future) |

---

## 3. Project Structure

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── api/                    # API client and hooks
│   │   ├── client.ts           # Axios/fetch wrapper with auth
│   │   ├── hooks/              # TanStack Query hooks
│   │   │   ├── useAgents.ts
│   │   │   ├── useTools.ts
│   │   │   ├── usePrompts.ts
│   │   │   ├── useSessions.ts
│   │   │   ├── useLLMProviders.ts
│   │   │   └── useAuth.ts
│   │   └── types.ts            # API response types
│   │
│   ├── components/             # Reusable components
│   │   ├── ui/                 # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── input.tsx
│   │   │   └── ...
│   │   ├── layout/             # Layout components
│   │   │   ├── AppLayout.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   └── PageContainer.tsx
│   │   ├── agents/             # Agent-specific components
│   │   │   ├── AgentCard.tsx
│   │   │   ├── AgentForm.tsx
│   │   │   ├── AgentVersionHistory.tsx
│   │   │   └── AgentTypeSelect.tsx
│   │   ├── tools/              # Tool-specific components
│   │   │   ├── ToolCard.tsx
│   │   │   ├── ToolForm.tsx
│   │   │   └── ToolCodeEditor.tsx
│   │   ├── prompts/            # Prompt-specific components
│   │   │   ├── PromptCard.tsx
│   │   │   ├── PromptForm.tsx
│   │   │   └── PromptPreview.tsx
│   │   ├── chat/               # Chat/playground components
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   └── TracePanel.tsx
│   │   ├── sessions/           # Session/trace components
│   │   │   ├── SessionList.tsx
│   │   │   ├── SessionDetail.tsx
│   │   │   ├── TraceTimeline.tsx
│   │   │   └── MetricsChart.tsx
│   │   └── providers/          # LLM provider components
│   │       ├── ProviderCard.tsx
│   │       ├── ProviderForm.tsx
│   │       └── ConnectionTest.tsx
│   │
│   ├── pages/                  # Route pages
│   │   ├── auth/
│   │   │   ├── LoginPage.tsx
│   │   │   └── RegisterPage.tsx
│   │   ├── dashboard/
│   │   │   └── DashboardPage.tsx
│   │   ├── agents/
│   │   │   ├── AgentListPage.tsx
│   │   │   ├── AgentDetailPage.tsx
│   │   │   └── AgentEditPage.tsx
│   │   ├── tools/
│   │   │   ├── ToolListPage.tsx
│   │   │   └── ToolEditPage.tsx
│   │   ├── prompts/
│   │   │   ├── PromptListPage.tsx
│   │   │   └── PromptEditPage.tsx
│   │   ├── playground/
│   │   │   └── PlaygroundPage.tsx
│   │   ├── sessions/
│   │   │   ├── SessionListPage.tsx
│   │   │   └── SessionDetailPage.tsx
│   │   └── settings/
│   │       ├── SettingsPage.tsx
│   │       └── ProvidersPage.tsx
│   │
│   ├── stores/                 # Zustand stores
│   │   ├── authStore.ts        # Auth state (user, token)
│   │   ├── uiStore.ts          # UI state (sidebar, theme)
│   │   └── chatStore.ts        # Chat state (current session)
│   │
│   ├── lib/                    # Utilities
│   │   ├── utils.ts            # cn() and helpers
│   │   ├── constants.ts        # App constants
│   │   └── validators.ts       # Zod schemas
│   │
│   ├── hooks/                  # Custom hooks
│   │   ├── useDebounce.ts
│   │   ├── useLocalStorage.ts
│   │   └── useMediaQuery.ts
│   │
│   ├── App.tsx                 # Root component with routing
│   ├── main.tsx                # Entry point
│   └── index.css               # Global styles + Tailwind
│
├── .env                        # Environment variables
├── .env.example
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
├── vite.config.ts
└── components.json             # shadcn/ui config
```

---

## 4. Routing Structure

```typescript
// App.tsx routes
const routes = [
  // Public routes
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },

  // Protected routes (require auth)
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <DashboardPage /> },

      // Agents
      { path: "agents", element: <AgentListPage /> },
      { path: "agents/new", element: <AgentEditPage /> },
      { path: "agents/:id", element: <AgentDetailPage /> },
      { path: "agents/:id/edit", element: <AgentEditPage /> },

      // Tools
      { path: "tools", element: <ToolListPage /> },
      { path: "tools/new", element: <ToolEditPage /> },
      { path: "tools/:id", element: <ToolEditPage /> },

      // Prompts
      { path: "prompts", element: <PromptListPage /> },
      { path: "prompts/new", element: <PromptEditPage /> },
      { path: "prompts/:id", element: <PromptEditPage /> },

      // Playground (Chat)
      { path: "playground", element: <PlaygroundPage /> },
      { path: "playground/:agentId", element: <PlaygroundPage /> },

      // Sessions
      { path: "sessions", element: <SessionListPage /> },
      { path: "sessions/:id", element: <SessionDetailPage /> },

      // Settings
      { path: "settings", element: <SettingsPage /> },
      { path: "settings/providers", element: <ProvidersPage /> },
    ]
  }
];
```

---

## 5. State Management

### Zustand Stores

#### Auth Store
```typescript
// stores/authStore.ts
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  updateUser: (user: User) => void;
}
```

#### UI Store
```typescript
// stores/uiStore.ts
interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark' | 'system';
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
}
```

#### Chat Store
```typescript
// stores/chatStore.ts
interface ChatState {
  currentAgentId: number | null;
  currentSessionId: number | null;
  messages: Message[];
  isLoading: boolean;
  setAgent: (id: number) => void;
  setSession: (id: number) => void;
  addMessage: (message: Message) => void;
  clearMessages: () => void;
}
```

### TanStack Query for Server State

All API data (agents, tools, prompts, sessions, providers) will be managed by TanStack Query:

```typescript
// api/hooks/useAgents.ts
export function useAgents(options?: { page?: number; search?: string }) {
  return useQuery({
    queryKey: ['agents', options],
    queryFn: () => api.agents.list(options),
  });
}

export function useAgent(id: number) {
  return useQuery({
    queryKey: ['agents', id],
    queryFn: () => api.agents.get(id),
  });
}

export function useCreateAgent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.agents.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
  });
}

export function useInvokeAgent() {
  return useMutation({
    mutationFn: ({ agentId, message }: { agentId: number; message: string }) =>
      api.agents.invoke(agentId, { message }),
  });
}
```

---

## 6. API Client

```typescript
// api/client.ts
import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

---

## 7. Authentication Flow

### Login Flow
1. User enters credentials on `/login`
2. POST to `/api/v1/auth/login`
3. Receive JWT token + user info
4. Store token in Zustand (persisted to localStorage)
5. Redirect to dashboard

### Protected Routes
```typescript
// components/ProtectedRoute.tsx
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
```

### Token Persistence
```typescript
// stores/authStore.ts
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      login: (token, user) => set({ token, user, isAuthenticated: true }),
      logout: () => set({ token: null, user: null, isAuthenticated: false }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ token: state.token, user: state.user }),
    }
  )
);
```

---

## 8. Page Specifications

### 8.1 Dashboard Page
**Route**: `/`

**Features**:
- Quick stats cards (total agents, sessions today, active providers)
- Recent agents list (last 5 modified)
- Recent sessions list (last 5)
- Quick action buttons (Create Agent, Open Playground)

**API Calls**:
- `GET /agents?limit=5&sort=-updated_at`
- `GET /sessions?limit=5&sort=-started_at`
- `GET /sessions/statistics`

---

### 8.2 Agent List Page
**Route**: `/agents`

**Features**:
- Grid/list view toggle
- Search by name/description
- Filter by agent type, tags
- Pagination
- Agent cards with:
  - Name, description, type badge
  - Tags
  - Last modified date
  - Actions: Edit, Clone, Delete, Open in Playground

**API Calls**:
- `GET /agents?page=1&limit=20&search=...&active_only=true`

---

### 8.3 Agent Edit Page
**Route**: `/agents/:id/edit` or `/agents/new`

**Features**:
- Tabbed interface:
  1. **General**: Name, description, type, tags
  2. **Model**: LLM provider selection, model, temperature, max tokens
  3. **Tools**: Assign tools from catalog with checkboxes
  4. **Prompts**: System prompt editor, prompt template selection
  5. **Advanced**: Timeout, reflection settings, memory config
- Version history sidebar (for existing agents)
- Save/Cancel buttons
- Unsaved changes warning

**API Calls**:
- `GET /agents/:id` (for edit)
- `GET /agents/:id/versions`
- `GET /tools` (for tool selection)
- `GET /prompts` (for prompt selection)
- `GET /llm-providers` (for provider dropdown)
- `POST /agents` or `PUT /agents/:id`

---

### 8.4 Tool List Page
**Route**: `/tools`

**Features**:
- List with search and category filter
- Built-in vs Custom filter
- Tool cards showing:
  - Name, description
  - Category badge
  - Type badge (built-in/custom)
  - For custom: Edit, Delete buttons
- Create Custom Tool button

**API Calls**:
- `GET /tools?page=1&limit=20&category=...&tool_type=...`

---

### 8.5 Tool Edit Page
**Route**: `/tools/:id` or `/tools/new`

**Features**:
- Tool name and description
- Category selector
- For custom tools:
  - Monaco code editor for function code
  - Input schema builder (JSON or form-based)
  - Output schema definition
  - Test tool button with sample input
- Read-only view for built-in tools

**API Calls**:
- `GET /tools/:id`
- `POST /tools` or `PUT /tools/:id`
- `POST /tools/:id/test`

---

### 8.6 Prompt List Page
**Route**: `/prompts`

**Features**:
- List with search
- Filter by use case, message type
- Prompt cards showing:
  - Name, use case badge
  - Preview of content (truncated)
  - Version count
  - Actions: Edit, Clone, Delete

**API Calls**:
- `GET /prompts?page=1&limit=20&use_case=...`

---

### 8.7 Prompt Edit Page
**Route**: `/prompts/:id` or `/prompts/new`

**Features**:
- Name, description, use case, message type
- Monaco editor for prompt content with variable highlighting
- Variable extraction preview
- Preview with sample data
- Version history sidebar
- A/B testing toggle (is_active per version)

**API Calls**:
- `GET /prompts/:id`
- `GET /prompts/:id/versions`
- `POST /prompts` or `PUT /prompts/:id`
- `POST /prompts/:id/preview`

---

### 8.8 Playground Page
**Route**: `/playground` or `/playground/:agentId`

**Features**:
- **Left Panel**: Chat interface
  - Agent selector dropdown
  - Message history (user/assistant bubbles)
  - Input box with send button
  - Loading indicator during execution
  - Markdown rendering for responses

- **Right Panel**: Execution trace
  - Collapsible trace steps
  - Step types with icons (thought, tool_call, tool_result, etc.)
  - Tool inputs/outputs
  - Timestamps and latency

- **Top Bar**:
  - Current agent name
  - Session info
  - New Session button
  - Settings (timeout, temp override)

**API Calls**:
- `GET /agents` (for dropdown)
- `POST /agents/:id/invoke` (for chat)
- `GET /sessions/:id` (for trace)
- `GET /sessions/:id/messages`
- `GET /sessions/:id/trace-steps`

---

### 8.9 Session List Page
**Route**: `/sessions`

**Features**:
- List of past sessions
- Filter by agent, status, date range
- Session rows showing:
  - Agent name
  - Status badge (completed/failed)
  - Started at, duration
  - Token usage
  - Input preview
- Click to view details

**API Calls**:
- `GET /sessions?page=1&limit=20&agent_id=...&status=...`

---

### 8.10 Session Detail Page
**Route**: `/sessions/:id`

**Features**:
- Session metadata header (agent, status, timestamps)
- Performance metrics (latency, tokens, cost)
- Full conversation history
- Complete trace timeline
- Expandable trace steps with tool I/O
- Replay button (opens in playground)

**API Calls**:
- `GET /sessions/:id`
- `GET /sessions/:id/messages`
- `GET /sessions/:id/trace-steps`

---

### 8.11 Settings Page
**Route**: `/settings`

**Features**:
- User profile (username, email)
- Theme toggle (light/dark/system)
- Link to LLM Providers page

---

### 8.12 LLM Providers Page
**Route**: `/settings/providers`

**Features**:
- List of configured providers
- Provider cards showing:
  - Name, provider type, model info
  - Status badge (active/inactive)
  - Last used date
  - Edit, Delete, Test buttons
- Add Provider button
- Provider form modal:
  - Name, provider type dropdown
  - API key input (masked)
  - Provider-specific config (org ID, base URL, etc.)
- Test Connection button

**API Calls**:
- `GET /llm-providers`
- `POST /llm-providers`
- `PUT /llm-providers/:id`
- `PUT /llm-providers/:id/api-key`
- `POST /llm-providers/:id/test`
- `DELETE /llm-providers/:id`

---

## 9. Component Design Patterns

### Card Pattern
```tsx
// Reusable card for list items
<Card>
  <CardHeader>
    <CardTitle>{name}</CardTitle>
    <CardDescription>{description}</CardDescription>
  </CardHeader>
  <CardContent>
    {/* Badges, metadata */}
  </CardContent>
  <CardFooter>
    {/* Action buttons */}
  </CardFooter>
</Card>
```

### Form Pattern
```tsx
// React Hook Form + Zod
const schema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
});

function AgentForm({ onSubmit, defaultValues }) {
  const form = useForm({
    resolver: zodResolver(schema),
    defaultValues,
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {/* ... */}
      </form>
    </Form>
  );
}
```

### Loading/Error States
```tsx
function AgentList() {
  const { data, isLoading, error } = useAgents();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  if (!data?.agents.length) return <EmptyState />;

  return (
    <div className="grid gap-4">
      {data.agents.map((agent) => (
        <AgentCard key={agent.id} agent={agent} />
      ))}
    </div>
  );
}
```

---

## 10. Styling Guidelines

### Tailwind Configuration
```js
// tailwind.config.js
module.exports = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        // ... shadcn/ui color system
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
```

### Color Scheme
- Primary: Blue (#3B82F6) - actions, links, focus states
- Success: Green (#22C55E) - completed, success messages
- Warning: Yellow (#EAB308) - warnings, pending states
- Danger: Red (#EF4444) - errors, delete actions
- Neutral: Gray scale for text and backgrounds

### Spacing
- Use Tailwind's spacing scale (4px base)
- Page padding: `p-6` (24px)
- Card padding: `p-4` (16px)
- Grid gap: `gap-4` (16px)

---

## 11. Implementation Phases

### Phase 1: Foundation (Days 1-3)
1. Project setup (Vite, React, TypeScript)
2. Install and configure shadcn/ui
3. Set up Tailwind CSS
4. Create folder structure
5. Set up routing (React Router)
6. Set up API client (Axios)
7. Set up Zustand stores
8. Set up TanStack Query
9. Create layout components (AppLayout, Sidebar, Header)
10. Implement authentication pages (Login, Register)

### Phase 2: Core Pages (Days 4-7)
11. Dashboard page with stats
12. Agent list page with search/filter
13. Agent detail/edit page (tabbed form)
14. Tool list page
15. Tool create/edit page with code editor
16. Prompt list page
17. Prompt create/edit page

### Phase 3: Playground & Sessions (Days 8-10)
18. Playground page with chat interface
19. Agent invocation integration
20. Trace panel component
21. Session list page
22. Session detail page with full trace

### Phase 4: Settings & Polish (Days 11-14)
23. Settings page
24. LLM Providers management page
25. Dark mode implementation
26. Error handling and loading states
27. Form validation polish
28. Responsive design adjustments
29. Testing and bug fixes

---

## 12. API Type Definitions

```typescript
// api/types.ts

// Auth
interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
}

// Agents
interface Agent {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  agent_type: 'ReAct' | 'Plan-and-Execute' | 'Conversational' | 'Custom';
  tags: string[];
  is_active: boolean;
  current_version_id: number | null;
  created_at: string;
  updated_at: string | null;
}

interface AgentVersion {
  id: number;
  agent_id: number;
  version_number: number;
  config: AgentConfig;
  created_at: string;
  created_by: number;
}

interface AgentConfig {
  llm_config: {
    provider_id: number;
    model: string;
    temperature: number;
    max_tokens: number;
  };
  tool_ids: number[];
  prompt_id: number | null;
  system_prompt: string | null;
  timeout_seconds: number;
}

// Invoke
interface InvokeRequest {
  message: string;
  session_id?: number;
  config_override?: Partial<AgentConfig>;
  timeout_seconds?: number;
}

interface InvokeResponse {
  success: boolean;
  output: string | null;
  error: string | null;
  error_type: string | null;
  session_id: number;
  token_usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
  latency_ms: number;
  steps: TraceStep[];
}

// Tools
interface Tool {
  id: number;
  name: string;
  description: string;
  tool_type: 'builtin' | 'custom';
  category: string;
  input_schema: object | null;
  output_schema: object | null;
  function_code: string | null;
  is_active: boolean;
}

// Prompts
interface Prompt {
  id: number;
  name: string;
  description: string | null;
  use_case: string;
  message_type: 'system' | 'user' | 'assistant';
  current_version_id: number | null;
  tags: string[];
}

interface PromptVersion {
  id: number;
  prompt_id: number;
  version_number: number;
  content: string;
  variables: string[];
  is_active: boolean;
}

// Sessions
interface Session {
  id: number;
  agent_id: number | null;
  status: 'pending' | 'running' | 'completed' | 'failed';
  title: string | null;
  started_at: string;
  completed_at: string | null;
  total_latency_ms: number | null;
  token_usage_input: number;
  token_usage_output: number;
  total_cost: number | null;
  error_message: string | null;
}

interface Message {
  id: number;
  session_id: number;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  sequence_number: number;
  created_at: string;
}

interface TraceStep {
  id: number;
  session_id: number;
  step_number: number;
  step_type: 'thought' | 'tool_call' | 'tool_result' | 'reflection' | 'error' | 'observation' | 'final_answer';
  content: string | null;
  tool_name: string | null;
  tool_input: object | null;
  tool_output: object | null;
  latency_ms: number | null;
  created_at: string;
}

// LLM Providers
interface LLMProvider {
  id: number;
  name: string;
  provider_type: 'openai' | 'anthropic' | 'google' | 'azure_openai' | 'ollama' | 'llamacpp';
  is_active: boolean;
  config: object;
  last_used_at: string | null;
  created_at: string;
}

// Pagination
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
```

---

## 13. Testing Strategy

### Unit Tests (Vitest)
- Component rendering tests
- Hook tests (custom hooks, store actions)
- Utility function tests

### Integration Tests
- API hook tests with MSW (Mock Service Worker)
- Form submission flows
- Authentication flows

### E2E Tests (Playwright - Future)
- Login/logout flow
- Create agent flow
- Chat with agent flow
- Session viewing flow

---

## 14. Performance Considerations

### Optimizations
- React.memo for expensive components
- useMemo/useCallback for computed values
- Virtual scrolling for long lists (react-virtual)
- Image lazy loading
- Code splitting per route (React.lazy)

### Caching Strategy (TanStack Query)
- Agents: staleTime 30s, cacheTime 5min
- Tools: staleTime 1min (rarely change)
- Sessions: staleTime 10s (frequently change)
- Providers: staleTime 1min

---

## 15. Environment Variables

```bash
# .env.example
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=DeepAgentStudio
```

---

## 16. Dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@tanstack/react-query": "^5.0.0",
    "zustand": "^4.4.0",
    "axios": "^1.6.0",
    "react-hook-form": "^7.48.0",
    "@hookform/resolvers": "^3.3.0",
    "zod": "^3.22.0",
    "@monaco-editor/react": "^4.6.0",
    "react-markdown": "^9.0.0",
    "date-fns": "^2.30.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0",
    "lucide-react": "^0.290.0",

    // shadcn/ui dependencies (added via CLI)
    "@radix-ui/react-dialog": "^1.0.0",
    "@radix-ui/react-dropdown-menu": "^2.0.0",
    "@radix-ui/react-tabs": "^1.0.0",
    // ... more Radix primitives

    "tailwindcss-animate": "^1.0.0",
    "class-variance-authority": "^0.7.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.3.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "eslint": "^8.54.0",
    "prettier": "^3.1.0",
    "vitest": "^1.0.0"
  }
}
```

---

## 17. Success Criteria

### MVP Completion
- [ ] User can log in and access protected routes
- [ ] User can view, create, edit, delete agents
- [ ] User can view, create, edit, delete tools
- [ ] User can view, create, edit, delete prompts
- [ ] User can chat with an agent in the playground
- [ ] User can view execution traces
- [ ] User can view past sessions
- [ ] User can configure LLM providers

### Quality Metrics
- Page load time < 2s
- Time to interactive < 3s
- All forms have validation
- All errors are handled gracefully
- Dark mode works consistently

---

**End of Frontend Specification**
