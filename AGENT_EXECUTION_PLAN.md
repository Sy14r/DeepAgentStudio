# Agent Execution Engine - Implementation Plan

**Created**: 2026-01-03
**Status**: Planning Phase
**Estimated Duration**: 2-3 weeks
**Priority**: ⭐ TOP PRIORITY - Blocks MVP completion

---

## Table of Contents

1. [Overview](#overview)
2. [Current State](#current-state)
3. [Goals](#goals)
4. [Architecture](#architecture)
5. [Implementation Phases](#implementation-phases)
6. [Detailed Tasks](#detailed-tasks)
7. [Integration Points](#integration-points)
8. [Testing Strategy](#testing-strategy)
9. [Risk Assessment](#risk-assessment)
10. [Success Criteria](#success-criteria)

---

## Overview

The Agent Execution Engine is the core component that brings DeepAgentStudio to life by enabling users to actually **run** their configured agents. This engine will:

- Execute LangChain agents with user input
- Use configured LLM providers (OpenAI, Anthropic)
- Execute tools during agent runs
- Record all interactions in sessions/traces
- Handle errors, timeouts, and retries
- Support different agent types (ReAct, Plan-and-Execute, etc.)

**Current Blocker Status**: ✅ UNBLOCKED (LLM provider integration complete)

---

## Current State

### ✅ What We Have

1. **LLM Provider Integration**
   - OpenAI and Anthropic clients ready
   - Encrypted API key storage
   - Provider configuration CRUD
   - Connection testing

2. **Agent Configuration Storage**
   - Agent models with versioning
   - LLM configuration (provider, model, temperature, etc.)
   - Reflection configuration
   - Memory configuration
   - Tool associations

3. **Tool Framework**
   - Tool catalog (built-in and custom)
   - Agent-tool associations
   - Tool metadata and schemas

4. **Session/Trace Infrastructure**
   - Session recording models
   - Message storage
   - Trace step tracking
   - Performance metrics tracking

5. **All Supporting Infrastructure**
   - Authentication
   - Database migrations
   - API framework
   - Error handling patterns

### ❌ What We Need

1. **LangChain Integration**
   - Agent executor service
   - Tool wrappers
   - Memory implementations
   - Prompt templates

2. **Execution API Endpoint**
   - `/api/agents/{id}/invoke` endpoint
   - Request/response handling
   - Async execution support

3. **Session Recording During Execution**
   - Real-time trace creation
   - Message recording
   - Token usage tracking
   - Error capture

4. **Tool Execution**
   - Dynamic tool loading
   - Tool execution sandboxing
   - Tool result handling

---

## Goals

### Primary Goals

1. **Enable Agent Execution**: Users can invoke agents with input and get responses
2. **Full Observability**: All executions are tracked in sessions with detailed traces
3. **Tool Support**: Agents can use assigned tools during execution
4. **Error Resilience**: Graceful handling of failures with useful error messages
5. **Provider Flexibility**: Support for different LLM providers transparently

### Secondary Goals

6. **Memory Support**: Basic buffer memory for conversation context
7. **Performance Tracking**: Accurate latency and token usage metrics
8. **Reflection Support**: Basic reflection iterations for ReAct agents
9. **Timeout Management**: Prevent runaway executions

### Non-Goals (Future Work)

- ❌ Streaming responses (separate phase)
- ❌ Batch processing (separate phase)
- ❌ Advanced memory (vector store, summary)
- ❌ Complex agent orchestration
- ❌ Agent-to-agent communication

---

## Architecture

### High-Level Flow

```
User Request
    ↓
API Endpoint (/api/agents/{id}/invoke)
    ↓
Agent Executor Service
    ↓
┌─────────────────────────────────────────┐
│  1. Load Agent Configuration            │
│  2. Initialize LLM Provider Client      │
│  3. Load Tools                          │
│  4. Setup Memory                        │
│  5. Create LangChain Agent              │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Execute Agent                          │
│  ├─ Session Creation                    │
│  ├─ Trace Recording                     │
│  ├─ Tool Execution                      │
│  ├─ LLM Calls                          │
│  └─ Result Collection                   │
└─────────────────────────────────────────┘
    ↓
Response to User
```

### Component Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    API Layer                             │
│  POST /api/agents/{id}/invoke                           │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────┴─────────────────────────────────────┐
│              Agent Executor Service                      │
│  ┌──────────────────────────────────────────────────┐   │
│  │ AgentExecutor                                    │   │
│  │  - load_agent_config()                          │   │
│  │  - initialize_llm()                             │   │
│  │  - load_tools()                                 │   │
│  │  - setup_memory()                               │   │
│  │  - execute()                                    │   │
│  └──────────────────────────────────────────────────┘   │
└──────┬───────────────────┬───────────────────┬───────────┘
       │                   │                   │
┌──────┴────────┐  ┌──────┴────────┐  ┌──────┴────────┐
│ LLM Provider  │  │ Tool Executor │  │ Session       │
│ Clients       │  │               │  │ Recorder      │
│ - OpenAI      │  │ - Load tools  │  │ - Messages    │
│ - Anthropic   │  │ - Execute     │  │ - Traces      │
└───────────────┘  │ - Wrap result │  │ - Metrics     │
                   └───────────────┘  └───────────────┘
```

### Data Flow

```
1. Request Flow:
   User → API → Executor → Agent Config → LLM Provider Config

2. Execution Flow:
   Agent → LangChain → LLM API → Tools → Results

3. Recording Flow:
   Execution Events → Session Recorder → Database

4. Response Flow:
   Results → API → User
```

---

## Implementation Phases

### Phase 1: Foundation (Days 1-3)
**Goal**: Set up basic LangChain integration and simple agent execution

**Deliverables**:
- [ ] LangChain dependencies installed
- [ ] Basic agent executor service
- [ ] Simple ReAct agent execution (no tools)
- [ ] LLM provider integration with LangChain
- [ ] Basic error handling

**Test Coverage**: Unit tests for service initialization

---

### Phase 2: API Endpoint (Days 4-5)
**Goal**: Expose agent execution via REST API

**Deliverables**:
- [ ] `POST /api/agents/{id}/invoke` endpoint
- [ ] Request validation (AgentInvokeRequest schema)
- [ ] Response formatting (AgentInvokeResponse schema)
- [ ] Authentication and authorization
- [ ] Basic rate limiting

**Test Coverage**: API integration tests

---

### Phase 3: Session Recording (Days 6-8)
**Goal**: Full observability - record all executions

**Deliverables**:
- [ ] Session creation on invoke
- [ ] Message recording (user input, agent responses)
- [ ] Trace step recording (thoughts, actions, observations)
- [ ] Token usage tracking
- [ ] Latency metrics
- [ ] Error capture

**Test Coverage**: Verify all execution events are recorded

---

### Phase 4: Tool Integration (Days 9-11)
**Goal**: Enable agents to use tools

**Deliverables**:
- [ ] Tool loading from agent configuration
- [ ] LangChain tool wrappers
- [ ] Tool execution during agent runs
- [ ] Tool result handling
- [ ] Tool call trace recording
- [ ] Error handling for tool failures

**Test Coverage**: Tests with various tools (calculator, web search, etc.)

---

### Phase 5: Memory & Advanced Features (Days 12-14)
**Goal**: Add memory and reflection support

**Deliverables**:
- [ ] Buffer memory implementation
- [ ] Conversation context management
- [ ] Basic reflection iterations
- [ ] Timeout management
- [ ] Retry logic for transient failures
- [ ] Cost calculation

**Test Coverage**: Memory persistence tests, timeout tests

---

### Phase 6: Polish & Production Ready (Days 15-16)
**Goal**: Production hardening

**Deliverables**:
- [ ] Comprehensive error messages
- [ ] Input validation improvements
- [ ] Performance optimization
- [ ] Logging and monitoring
- [ ] Documentation
- [ ] End-to-end tests

**Test Coverage**: Full integration test suite

---

## Detailed Tasks

### Task 1: Install LangChain Dependencies

**File**: `backend/requirements.txt`

```python
# Add these dependencies
langchain>=0.1.0
langchain-openai>=0.0.5
langchain-anthropic>=0.1.0
langchain-community>=0.0.20
```

**Commands**:
```bash
# Update requirements
echo "langchain>=0.1.0" >> backend/requirements.txt
echo "langchain-openai>=0.0.5" >> backend/requirements.txt
echo "langchain-anthropic>=0.1.0" >> backend/requirements.txt
echo "langchain-community>=0.0.20" >> backend/requirements.txt

# Rebuild container
docker-compose build backend
```

---

### Task 2: Create Agent Executor Service

**File**: `backend/app/services/agent_executor.py`

**Purpose**: Core service that executes agents using LangChain

**Key Components**:

```python
class AgentExecutor:
    """
    Service for executing LangChain agents.

    Responsibilities:
    - Load agent configuration from database
    - Initialize LLM provider client
    - Load and prepare tools
    - Setup memory
    - Execute agent with input
    - Record execution in session/traces
    """

    def __init__(self, db: Session):
        self.db = db

    async def execute(
        self,
        agent_id: int,
        user_id: int,
        input_text: str,
        session_id: Optional[int] = None
    ) -> AgentExecutionResult:
        """Execute an agent with given input"""
        # 1. Load agent configuration
        # 2. Validate user access
        # 3. Create/resume session
        # 4. Initialize LLM
        # 5. Load tools
        # 6. Setup memory
        # 7. Execute agent
        # 8. Record traces
        # 9. Return results
        pass

    def _load_agent_config(self, agent_id: int, user_id: int) -> Agent:
        """Load agent with current version config"""
        pass

    def _initialize_llm(self, llm_config: dict, user_id: int):
        """Initialize LLM provider client"""
        pass

    def _load_tools(self, tool_ids: List[int]) -> List[BaseTool]:
        """Load and wrap tools for LangChain"""
        pass

    def _setup_memory(self, memory_config: dict):
        """Setup memory for agent"""
        pass

    def _create_langchain_agent(self, llm, tools, memory, agent_type: str):
        """Create appropriate LangChain agent"""
        pass

    def _record_session(self, session, messages, traces, metrics):
        """Record execution in database"""
        pass
```

**Dependencies**:
- Agent model
- LLM provider clients
- Tool models
- Session models

---

### Task 3: Create LLM Provider Adapter

**File**: `backend/app/services/llm_adapter.py`

**Purpose**: Adapt our LLM clients to LangChain's interface

**Key Components**:

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

class LLMProviderAdapter:
    """
    Adapter to create LangChain-compatible LLM instances
    from our provider configurations.
    """

    @staticmethod
    def create_llm(provider_config: LLMProviderConfig, llm_config: dict):
        """
        Create a LangChain LLM instance.

        Args:
            provider_config: LLMProviderConfig from database
            llm_config: Agent's LLM configuration

        Returns:
            LangChain BaseChatModel instance
        """
        # Decrypt API key
        api_key = decrypt_api_key(provider_config.encrypted_api_key)

        provider_type = provider_config.provider_type

        if provider_type == "openai":
            return ChatOpenAI(
                api_key=api_key,
                model=llm_config.get("model", "gpt-4"),
                temperature=llm_config.get("temperature", 0.7),
                max_tokens=llm_config.get("max_tokens"),
                # ... other config
            )

        elif provider_type == "anthropic":
            return ChatAnthropic(
                api_key=api_key,
                model=llm_config.get("model", "claude-3-5-sonnet-20241022"),
                temperature=llm_config.get("temperature", 0.7),
                max_tokens=llm_config.get("max_tokens", 1024),
                # ... other config
            )

        else:
            raise ValueError(f"Unsupported provider: {provider_type}")
```

---

### Task 4: Create Tool Wrappers

**File**: `backend/app/services/tool_wrapper.py`

**Purpose**: Wrap our Tool models as LangChain tools

**Key Components**:

```python
from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field

class ToolWrapper(BaseTool):
    """
    Wraps a DeepAgentStudio Tool as a LangChain tool.
    """
    tool_id: int
    name: str
    description: str
    tool_code: str

    def _run(self, *args, **kwargs) -> str:
        """Execute the tool"""
        # Execute tool code safely
        # Return result as string
        pass

    async def _arun(self, *args, **kwargs) -> str:
        """Async execution"""
        return self._run(*args, **kwargs)


class ToolLoader:
    """Loads tools from database and wraps them for LangChain"""

    @staticmethod
    def load_tools(db: Session, tool_ids: List[int]) -> List[BaseTool]:
        """
        Load tools from database and wrap for LangChain.

        Args:
            db: Database session
            tool_ids: List of tool IDs to load

        Returns:
            List of LangChain-compatible tools
        """
        tools = []
        for tool_id in tool_ids:
            tool = db.query(Tool).filter(Tool.id == tool_id).first()
            if tool:
                wrapped_tool = ToolWrapper(
                    tool_id=tool.id,
                    name=tool.name,
                    description=tool.description,
                    tool_code=tool.code
                )
                tools.append(wrapped_tool)
        return tools
```

**Security Note**: Tool execution needs sandboxing - use RestrictedPython or separate process

---

### Task 5: Create Invoke API Endpoint

**File**: `backend/app/api/v1/agents.py` (add to existing file)

**Schemas** (`backend/app/schemas/agent.py`):

```python
class AgentInvokeRequest(BaseModel):
    """Request to invoke an agent"""
    input: str = Field(..., min_length=1, max_length=10000, description="User input to the agent")
    session_id: Optional[int] = Field(None, description="Resume existing session")
    config_overrides: Optional[Dict[str, Any]] = Field(None, description="Override agent config")


class AgentInvokeResponse(BaseModel):
    """Response from agent invocation"""
    session_id: int = Field(..., description="Session ID for this execution")
    output: str = Field(..., description="Agent's response")
    status: str = Field(..., description="Execution status: success, error, timeout")

    # Metadata
    steps_taken: int = Field(..., description="Number of reasoning steps")
    tools_used: List[str] = Field(default_factory=list, description="Tools called during execution")

    # Metrics
    latency_ms: int = Field(..., description="Total execution time")
    tokens_used: int = Field(..., description="Total tokens consumed")
    estimated_cost: float = Field(..., description="Estimated cost in USD")

    # Error info (if status == "error")
    error: Optional[str] = Field(None, description="Error message if execution failed")

    # Trace info
    trace_url: Optional[str] = Field(None, description="URL to view detailed traces")
```

**Endpoint**:

```python
@router.post("/{agent_id}/invoke", response_model=AgentInvokeResponse)
async def invoke_agent(
    agent_id: int,
    request: AgentInvokeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Execute an agent with user input.

    This endpoint:
    1. Validates agent ownership
    2. Creates/resumes a session
    3. Executes the agent
    4. Records all traces
    5. Returns the result

    The execution is fully observable - check the session traces
    for step-by-step details.
    """
    # Verify agent ownership
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is not active"
        )

    # Execute agent
    executor = AgentExecutor(db)

    try:
        result = await executor.execute(
            agent_id=agent_id,
            user_id=current_user.id,
            input_text=request.input,
            session_id=request.session_id,
            config_overrides=request.config_overrides
        )

        return AgentInvokeResponse(
            session_id=result.session_id,
            output=result.output,
            status="success",
            steps_taken=result.steps_taken,
            tools_used=result.tools_used,
            latency_ms=result.latency_ms,
            tokens_used=result.tokens_used,
            estimated_cost=result.estimated_cost,
            trace_url=f"/api/v1/sessions/{result.session_id}"
        )

    except TimeoutError as e:
        return AgentInvokeResponse(
            session_id=result.session_id if result else None,
            output="",
            status="timeout",
            error=str(e),
            # ... other fields
        )

    except Exception as e:
        # Log error
        logger.error(f"Agent execution failed: {str(e)}", exc_info=True)

        return AgentInvokeResponse(
            session_id=result.session_id if result else None,
            output="",
            status="error",
            error=str(e),
            # ... other fields
        )
```

---

### Task 6: Implement Session Recording

**File**: `backend/app/services/session_recorder.py`

**Purpose**: Record execution events in real-time

**Key Components**:

```python
class SessionRecorder:
    """
    Records agent execution in sessions, messages, and traces.
    """

    def __init__(self, db: Session):
        self.db = db
        self.session = None
        self.start_time = None

    def start_session(
        self,
        agent_id: int,
        user_id: int,
        session_id: Optional[int] = None
    ) -> Session:
        """Create or resume a session"""
        if session_id:
            # Resume existing session
            session = self.db.query(Session).filter(
                Session.id == session_id,
                Session.user_id == user_id
            ).first()
            if not session:
                raise ValueError("Session not found")
            self.session = session
        else:
            # Create new session
            self.session = Session(
                agent_id=agent_id,
                user_id=user_id,
                status="running",
                started_at=datetime.utcnow()
            )
            self.db.add(self.session)
            self.db.flush()

        self.start_time = time.time()
        return self.session

    def record_user_message(self, content: str):
        """Record user input"""
        message = Message(
            session_id=self.session.id,
            role="user",
            content=content,
            timestamp=datetime.utcnow()
        )
        self.db.add(message)
        self.db.flush()

    def record_agent_message(self, content: str):
        """Record agent output"""
        message = Message(
            session_id=self.session.id,
            role="assistant",
            content=content,
            timestamp=datetime.utcnow()
        )
        self.db.add(message)
        self.db.flush()

    def record_trace_step(
        self,
        step_type: str,
        content: str,
        metadata: dict = None
    ):
        """Record a trace step"""
        step_number = self.db.query(TraceStep).filter(
            TraceStep.session_id == self.session.id
        ).count() + 1

        trace = TraceStep(
            session_id=self.session.id,
            step_number=step_number,
            step_type=step_type,
            content=content,
            metadata=metadata or {},
            timestamp=datetime.utcnow()
        )
        self.db.add(trace)
        self.db.flush()

    def finish_session(
        self,
        status: str,
        output: str,
        tokens_used: int,
        cost: float,
        error: Optional[str] = None
    ):
        """Finalize session with metrics"""
        self.session.status = status
        self.session.output = output
        self.session.completed_at = datetime.utcnow()
        self.session.total_tokens = tokens_used
        self.session.estimated_cost = cost
        self.session.latency_ms = int((time.time() - self.start_time) * 1000)

        if error:
            self.session.error_message = error

        self.db.commit()
```

---

## Integration Points

### 1. LLM Provider Integration

**Connection**: `AgentExecutor` → `LLMProviderAdapter` → LLM Provider Clients

**Flow**:
```python
# In AgentExecutor.execute():

# Get provider config from agent's LLM config
provider_id = agent_config["llm_config"]["provider_id"]
provider_config = db.query(LLMProviderConfig).filter(
    LLMProviderConfig.id == provider_id,
    LLMProviderConfig.user_id == user_id
).first()

# Create LangChain LLM
llm = LLMProviderAdapter.create_llm(
    provider_config=provider_config,
    llm_config=agent_config["llm_config"]
)
```

**Error Handling**: Catch provider errors and record in session

---

### 2. Tool Integration

**Connection**: `AgentExecutor` → `ToolLoader` → Tool Models

**Flow**:
```python
# In AgentExecutor.execute():

# Get tool IDs from agent config
tool_ids = agent_config["tool_ids"]

# Load tools
tools = ToolLoader.load_tools(db, tool_ids)

# Use in agent creation
agent = create_react_agent(llm=llm, tools=tools, ...)
```

**Error Handling**: Tool failures should be captured as trace steps

---

### 3. Session Recording

**Connection**: `AgentExecutor` → `SessionRecorder` → Session/Message/TraceStep models

**Flow**:
```python
# In AgentExecutor.execute():

recorder = SessionRecorder(db)

# Start session
session = recorder.start_session(agent_id, user_id, session_id)

# Record user input
recorder.record_user_message(input_text)

# During execution - record each step
recorder.record_trace_step("thought", agent_thought)
recorder.record_trace_step("tool_call", tool_name, metadata={"input": tool_input})
recorder.record_trace_step("observation", tool_output)

# Record final output
recorder.record_agent_message(final_output)

# Finish with metrics
recorder.finish_session(
    status="success",
    output=final_output,
    tokens_used=total_tokens,
    cost=estimated_cost
)
```

---

## Testing Strategy

### Unit Tests

**File**: `backend/tests/test_agent_executor.py`

**Coverage**:
- [ ] Test agent config loading
- [ ] Test LLM initialization (mocked)
- [ ] Test tool loading
- [ ] Test memory setup
- [ ] Test session recording
- [ ] Test error handling

**Approach**: Mock LangChain components, test our wrappers

---

### Integration Tests

**File**: `backend/tests/test_agent_execution_integration.py`

**Coverage**:
- [ ] Test full agent execution with mocked LLM
- [ ] Test tool execution
- [ ] Test session recording
- [ ] Test error scenarios
- [ ] Test timeout handling

**Approach**: Use real database, mock LLM API calls

---

### API Tests

**File**: `backend/tests/test_agent_invoke_api.py`

**Coverage**:
- [ ] Test invoke endpoint success
- [ ] Test authentication
- [ ] Test agent ownership validation
- [ ] Test error responses
- [ ] Test session creation/resumption

**Approach**: Full API testing with TestClient

---

### Optional: Real LLM Tests

**File**: `backend/tests/test_agent_execution_real.py`

**Marker**: `@pytest.mark.integration`

**Coverage**:
- [ ] Test with real OpenAI API
- [ ] Test with real Anthropic API
- [ ] Test tool execution with real LLM

**Warning**: ⚠️ These tests cost money and are skipped by default

---

## Risk Assessment

### High Risk

**Risk**: LangChain API changes
**Mitigation**: Pin LangChain versions, thorough testing
**Impact**: Medium - would require code updates

**Risk**: Tool execution security vulnerabilities
**Mitigation**: Implement sandboxing, input validation
**Impact**: High - could allow arbitrary code execution

**Risk**: Runaway LLM costs
**Mitigation**: Implement timeouts, token limits, cost warnings
**Impact**: High - could incur unexpected costs

### Medium Risk

**Risk**: Performance issues with complex agents
**Mitigation**: Implement timeouts, async execution
**Impact**: Medium - slow user experience

**Risk**: Session recording failures
**Mitigation**: Wrap in try/catch, log errors
**Impact**: Low - execution continues even if recording fails

### Low Risk

**Risk**: Memory leaks in long-running agents
**Mitigation**: Proper cleanup, resource limits
**Impact**: Low - agents run in isolated requests

---

## Success Criteria

### Must Have ✅

- [ ] User can invoke an agent via API
- [ ] Agent executes and returns a response
- [ ] All executions are recorded in sessions
- [ ] Traces show step-by-step execution
- [ ] Tools can be used during execution
- [ ] Errors are handled gracefully
- [ ] Token usage is tracked
- [ ] 90%+ test coverage

### Should Have 🎯

- [ ] Buffer memory works across conversation
- [ ] Reflection iterations work for ReAct agents
- [ ] Timeout prevents runaway executions
- [ ] Cost estimation is accurate
- [ ] Performance is acceptable (< 30s for most agents)

### Nice to Have 💡

- [ ] Multiple agent types supported (ReAct, Plan-and-Execute)
- [ ] Config overrides work
- [ ] Session resumption works correctly
- [ ] Detailed error messages for debugging

---

## Timeline

### Week 1: Foundation
- **Days 1-2**: LangChain setup, basic executor service
- **Day 3**: LLM provider adapter
- **Days 4-5**: API endpoint

### Week 2: Core Features
- **Days 6-7**: Session recording
- **Days 8-9**: Tool integration
- **Day 10**: Memory support

### Week 3: Polish
- **Days 11-12**: Error handling, timeouts
- **Day 13**: Testing
- **Day 14**: Documentation
- **Days 15-16**: Buffer for unexpected issues

---

## Next Steps

### Immediate Actions

1. **Review this plan** - Discuss any concerns or changes
2. **Install dependencies** - Add LangChain to requirements.txt
3. **Start Phase 1** - Create basic executor service
4. **Set up test framework** - Create test files with fixtures

### Before Starting

- [ ] Review LangChain documentation
- [ ] Understand ReAct agent pattern
- [ ] Review existing codebase integration points
- [ ] Set up development environment with LangChain

### Questions Answered ✅

1. **Agent Types**: Support both ReAct AND Plan-and-Execute from day 1
2. **Timeouts**: Default 30s, but fully user-configurable in agent config (100s-1000s allowed)
3. **Tool Security**: Create a `SandboxService` abstraction now (no-op implementation) for easy future sandboxing
4. **Cost Limits**: No warnings or hard limits for now
5. **Rate Limiting**: Sane defaults, but configurable for later adjustment

---

## Appendix: Code Examples

### Example: Complete Agent Execution Flow

```python
# In agent_executor.py

async def execute(
    self,
    agent_id: int,
    user_id: int,
    input_text: str,
    session_id: Optional[int] = None
) -> AgentExecutionResult:
    """Execute an agent end-to-end"""

    # 1. Load agent
    agent = self._load_agent_config(agent_id, user_id)
    agent_config = agent.current_version.config

    # 2. Start session recording
    recorder = SessionRecorder(self.db)
    session = recorder.start_session(agent_id, user_id, session_id)
    recorder.record_user_message(input_text)

    try:
        # 3. Initialize LLM
        provider_id = agent_config["llm_config"]["provider_id"]
        provider_config = self.db.query(LLMProviderConfig).filter(
            LLMProviderConfig.id == provider_id,
            LLMProviderConfig.user_id == user_id
        ).first()

        llm = LLMProviderAdapter.create_llm(
            provider_config,
            agent_config["llm_config"]
        )

        # 4. Load tools
        tools = ToolLoader.load_tools(
            self.db,
            agent_config.get("tool_ids", [])
        )

        # 5. Setup memory
        memory = self._setup_memory(agent_config.get("memory_config", {}))

        # 6. Create LangChain agent
        langchain_agent = create_react_agent(
            llm=llm,
            tools=tools,
            prompt=self._get_agent_prompt(agent_config)
        )

        agent_executor = AgentExecutor(
            agent=langchain_agent,
            tools=tools,
            memory=memory,
            max_iterations=agent_config.get("reflection_config", {}).get("iteration_limit", 5),
            max_execution_time=120,  # 2 minute timeout
            verbose=True
        )

        # 7. Execute with recording
        start_time = time.time()

        # Hook into LangChain callbacks to record traces
        result = await agent_executor.ainvoke(
            {"input": input_text},
            config={"callbacks": [SessionRecorderCallback(recorder)]}
        )

        output = result["output"]

        # 8. Calculate metrics
        execution_time = int((time.time() - start_time) * 1000)
        tokens_used = self._count_tokens(result)  # Extract from result
        cost = self._estimate_cost(tokens_used, provider_config.provider_type)

        # 9. Record completion
        recorder.record_agent_message(output)
        recorder.finish_session(
            status="success",
            output=output,
            tokens_used=tokens_used,
            cost=cost
        )

        return AgentExecutionResult(
            session_id=session.id,
            output=output,
            status="success",
            steps_taken=len(result.get("intermediate_steps", [])),
            tools_used=[step[0].tool for step in result.get("intermediate_steps", [])],
            latency_ms=execution_time,
            tokens_used=tokens_used,
            estimated_cost=cost
        )

    except TimeoutError as e:
        recorder.finish_session(
            status="timeout",
            output="",
            tokens_used=0,
            cost=0.0,
            error=str(e)
        )
        raise

    except Exception as e:
        recorder.finish_session(
            status="error",
            output="",
            tokens_used=0,
            cost=0.0,
            error=str(e)
        )
        raise
```

---

**End of Implementation Plan**

This plan is a living document and will be updated as implementation progresses.
