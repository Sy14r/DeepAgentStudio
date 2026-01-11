# DeepAgentStudio - Evaluations System Specification

**Version**: 1.1
**Created**: 2026-01-08
**Last Updated**: 2026-01-08
**Status**: Backend Complete, Frontend In Progress

---

## Implementation Progress

| Phase | Description | Status | Files |
|-------|-------------|--------|-------|
| 1 | Database & Core Backend | ✅ Complete | Migration, models, schemas, dataset_service, evaluator_service |
| 2 | Evaluator Engine | ✅ Complete | evaluator_engine.py (17 evaluators) |
| 3 | Evaluation Runner | ✅ Complete | evaluation_runner.py |
| 4 | REST API | ✅ Complete | evaluations.py (24 endpoints) |
| 5 | Frontend - Datasets | 🔲 Not Started | - |
| 6 | Frontend - Evaluators | 🔲 Not Started | - |
| 7 | Frontend - Evaluation Runs | 🔲 Not Started | - |
| 8 | Comparison & Polish | 🔲 Not Started | - |

### Backend Files Created
- `backend/alembic/versions/a1b2c3d4e5f6_add_evaluation_tables.py` - Database migration
- `backend/app/models/evaluation.py` - 6 SQLAlchemy models, 4 enums
- `backend/app/schemas/evaluation.py` - 40+ Pydantic schemas
- `backend/app/services/dataset_service.py` - Dataset & example CRUD with import/export
- `backend/app/services/evaluator_service.py` - Evaluator CRUD with 17 built-in definitions
- `backend/app/services/evaluator_engine.py` - All evaluator implementations
- `backend/app/services/evaluation_runner.py` - Async execution orchestrator
- `backend/app/api/v1/evaluations.py` - 24 REST API endpoints

### Notes
- Built-in evaluators seeded automatically on app startup
- LLM Judge and Semantic Similarity evaluators are placeholders (need LLM/embedding API integration)
- Custom Code evaluator placeholder (needs sandboxing implementation)

---

## Executive Summary

This specification defines an Evaluations system for DeepAgentStudio that enables users to systematically test and measure agent performance. The system supports creating evaluation datasets (collections of input-expected output pairs), running agents against these datasets, and evaluating results using two categories of configurable evaluators:

1. **Output Evaluators** - Judge the quality of agent responses (exact match, semantic similarity, LLM-as-judge, custom code)
2. **Run Metadata Evaluators** - Judge operational efficiency (token usage, latency, tool selection, error rates, chain length)

## Goals

1. **Systematic Testing**: Enable repeatable, automated testing of agent configurations
2. **Output Quality**: Measure correctness and quality of agent responses
3. **Operational Efficiency**: Track token usage, latency, cost, and tool selection
4. **Performance Tracking**: Track agent performance over time and across versions
5. **Quality Assurance**: Catch regressions before deploying agent changes
6. **Comparison**: Compare different agent configurations side-by-side
7. **Insight**: Understand where agents succeed and fail through detailed analysis

## Core Concepts

### 1. Evaluation Dataset

A collection of test cases (examples) used to evaluate agent performance.

**Properties:**
- `id`: Unique identifier
- `name`: Human-readable name (e.g., "Customer Support QA", "Code Generation Tests")
- `description`: Detailed description of what this dataset tests
- `schema_type`: Type of examples - "text" (simple Q&A) or "structured" (JSON schema)
- `input_schema`: Optional JSON schema for structured inputs
- `output_schema`: Optional JSON schema for structured expected outputs
- `tags`: Categorization tags
- `example_count`: Cached count of examples
- `created_at`, `updated_at`
- `user_id`: Owner

### 2. Dataset Example

A single test case within a dataset.

**Properties:**
- `id`: Unique identifier
- `dataset_id`: Parent dataset
- `name`: Optional name/label for the example
- `input`: The input to send to the agent (text or JSON)
- `expected_output`: The expected/ground truth output (text or JSON)
- `context`: Optional additional context (e.g., reference documents)
- `metadata`: Arbitrary JSON metadata (difficulty, category, source, etc.)
- `tags`: Example-level tags for filtering
- `created_at`, `updated_at`

### 3. Evaluator

Defines how to judge agent outputs and/or run metadata.

**Evaluator Categories:**

Evaluators fall into two categories:
1. **Output Evaluators** - Judge the final output against expected output
2. **Run Metadata Evaluators** - Judge operational aspects of the agent run (efficiency, reliability, tool usage)

**Built-in Output Evaluator Types:**

| Type | Description | Configuration |
|------|-------------|---------------|
| `exact_match` | Exact string equality | `case_sensitive`, `strip_whitespace` |
| `contains` | Output contains expected | `case_sensitive` |
| `regex_match` | Output matches regex pattern | `pattern`, `flags` |
| `json_match` | JSON structure equality | `ignore_order`, `subset_match` |
| `semantic_similarity` | Embedding-based similarity | `threshold` (0-1), `model` |
| `llm_judge` | LLM evaluates correctness | `prompt_template`, `model`, `criteria` |
| `custom_code` | User-defined Python function | `function_code` |

**Built-in Run Metadata Evaluator Types:**

| Type | Description | Configuration |
|------|-------------|---------------|
| `token_efficiency` | Tokens used relative to output length | `max_ratio`, `input_weight`, `output_weight` |
| `latency_threshold` | Response time within threshold | `max_ms`, `warning_ms` |
| `cost_threshold` | Cost within budget | `max_cost`, `warning_cost` |
| `chain_length` | Number of agent iterations | `max_steps`, `warning_steps` |
| `tool_call_success_rate` | Percentage of successful tool calls | `min_success_rate` |
| `tool_selection` | Correct tools used for task | `required_tools`, `forbidden_tools`, `mode` |
| `error_rate` | Errors/retries during execution | `max_errors`, `max_retries` |
| `span_count` | Total spans within threshold | `max_spans`, `span_types` |
| `custom_metadata` | Custom Python function on run metadata | `function_code` |

**Evaluator Properties:**
- `id`: Unique identifier
- `name`: Human-readable name
- `type`: One of the types above
- `category`: "output" or "run_metadata"
- `description`: What this evaluator checks
- `config`: Type-specific configuration JSON
- `is_builtin`: System-provided vs user-created
- `user_id`: Owner (null for built-in)
- `created_at`, `updated_at`

### 3a. Run Metadata Schema

The following metadata is captured for each example run and available to run metadata evaluators:

```json
{
  "latency_ms": 2340,
  "token_usage": {
    "input": 1250,
    "output": 380,
    "total": 1630
  },
  "cost_usd": 0.0045,
  "chain_length": 4,
  "tool_calls": {
    "total": 5,
    "successful": 4,
    "failed": 1,
    "tools_used": ["web_search", "file_write", "python_exec"],
    "call_details": [
      {
        "tool_name": "web_search",
        "success": true,
        "latency_ms": 450,
        "error": null
      },
      {
        "tool_name": "python_exec",
        "success": false,
        "latency_ms": 120,
        "error": "SyntaxError: invalid syntax"
      }
    ]
  },
  "llm_calls": {
    "total": 4,
    "models_used": ["gpt-4o"],
    "total_tokens": 1630
  },
  "spans": {
    "total": 12,
    "by_type": {
      "llm": 4,
      "tool": 5,
      "chain": 2,
      "agent": 1
    },
    "errors": 1
  },
  "retries": 0,
  "memory_operations": {
    "reads": 2,
    "writes": 1
  }
}
```

### 4. Evaluation Run

An execution of a dataset against an agent configuration.

**Properties:**
- `id`: Unique identifier
- `name`: Optional run name (auto-generated if not provided)
- `dataset_id`: Which dataset to run
- `agent_id`: Which agent to evaluate
- `agent_version_id`: Optional specific agent version (latest if not specified)
- `evaluator_ids`: List of evaluators to apply (multiple evaluators per run)
- `status`: "pending" | "running" | "completed" | "failed" | "cancelled"
- `progress`: Percentage complete (0-100)
- `total_examples`: Number of examples in run
- `completed_examples`: Number processed
- `config`: Run configuration (concurrency, timeout, etc.)
- `started_at`, `completed_at`
- `created_at`
- `user_id`: Who initiated the run

**Run Configuration:**
```json
{
  "concurrency": 3,
  "timeout_per_example_ms": 60000,
  "retry_failed": false,
  "max_retries": 2,
  "sample_size": null,
  "sample_seed": null
}
```

### 5. Evaluation Result

Result for a single example in a run.

**Properties:**
- `id`: Unique identifier
- `run_id`: Parent evaluation run
- `example_id`: Which dataset example
- `agent_output`: What the agent actually produced
- `session_id`: Link to full session for detailed trace
- `run_metadata`: Captured operational metadata (see 3a. Run Metadata Schema)
- `status`: "pending" | "running" | "completed" | "failed" | "error"
- `latency_ms`: Time to get agent response
- `token_usage_input`: Input tokens used
- `token_usage_output`: Output tokens used
- `cost`: Cost of this invocation
- `error_message`: If status is "error"
- `created_at`, `completed_at`

### 6. Evaluation Score

Individual evaluator score for a result.

**Properties:**
- `id`: Unique identifier
- `result_id`: Parent evaluation result
- `evaluator_id`: Which evaluator
- `score`: Numeric score (0.0 - 1.0)
- `passed`: Boolean pass/fail (score >= threshold)
- `feedback`: Evaluator explanation/reasoning
- `metadata`: Additional evaluator-specific data
- `created_at`

## Aggregate Metrics

### Run-Level Metrics

Calculated and cached on the evaluation run:

```json
{
  "total_examples": 100,
  "completed": 98,
  "failed": 2,
  "pass_rate": 0.85,
  "avg_score": 0.87,
  "avg_latency_ms": 2340,
  "total_tokens": 45000,
  "total_cost": 0.45,
  "score_distribution": {
    "0.0-0.2": 5,
    "0.2-0.4": 3,
    "0.4-0.6": 7,
    "0.6-0.8": 15,
    "0.8-1.0": 68
  },
  "evaluator_scores": {
    "exact_match": { "pass_rate": 0.75, "avg_score": 0.75, "category": "output" },
    "llm_judge": { "pass_rate": 0.92, "avg_score": 0.89, "category": "output" },
    "token_efficiency": { "pass_rate": 0.88, "avg_score": 0.91, "category": "run_metadata" },
    "tool_call_success_rate": { "pass_rate": 0.95, "avg_score": 0.97, "category": "run_metadata" }
  },
  "tag_breakdown": {
    "easy": { "count": 30, "pass_rate": 0.95 },
    "medium": { "count": 50, "pass_rate": 0.85 },
    "hard": { "count": 20, "pass_rate": 0.70 }
  },
  "run_metadata_aggregates": {
    "avg_chain_length": 3.2,
    "avg_tool_calls": 4.5,
    "tool_success_rate": 0.94,
    "total_tool_calls": 450,
    "failed_tool_calls": 27,
    "tools_used_distribution": {
      "web_search": 120,
      "python_exec": 85,
      "file_write": 65,
      "file_read": 180
    },
    "avg_llm_calls": 3.8,
    "avg_spans_per_run": 12.4,
    "error_rate": 0.03
  }
}
```

---

## Database Schema

### New Tables

```sql
-- Evaluation Datasets
CREATE TABLE evaluation_datasets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    schema_type VARCHAR(20) DEFAULT 'text',  -- 'text' or 'structured'
    input_schema JSONB,
    output_schema JSONB,
    tags VARCHAR(255)[],
    example_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Dataset Examples
CREATE TABLE dataset_examples (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES evaluation_datasets(id) ON DELETE CASCADE,
    name VARCHAR(255),
    input JSONB NOT NULL,
    expected_output JSONB NOT NULL,
    context JSONB,
    metadata JSONB,
    tags VARCHAR(255)[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Evaluators
CREATE TABLE evaluators (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),  -- NULL for built-in
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    category VARCHAR(20) DEFAULT 'output',  -- 'output' or 'run_metadata'
    description TEXT,
    config JSONB NOT NULL DEFAULT '{}',
    is_builtin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Evaluation Runs
CREATE TABLE evaluation_runs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(255),
    dataset_id INTEGER REFERENCES evaluation_datasets(id),
    agent_id INTEGER REFERENCES agents(id),
    agent_version_id INTEGER REFERENCES agent_versions(id),
    status VARCHAR(20) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    total_examples INTEGER DEFAULT 0,
    completed_examples INTEGER DEFAULT 0,
    config JSONB DEFAULT '{}',
    metrics JSONB,  -- Cached aggregate metrics
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Many-to-many: Runs to Evaluators
CREATE TABLE evaluation_run_evaluators (
    run_id INTEGER REFERENCES evaluation_runs(id) ON DELETE CASCADE,
    evaluator_id INTEGER REFERENCES evaluators(id),
    PRIMARY KEY (run_id, evaluator_id)
);

-- Evaluation Results (per example)
CREATE TABLE evaluation_results (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES evaluation_runs(id) ON DELETE CASCADE,
    example_id INTEGER REFERENCES dataset_examples(id),
    session_id INTEGER REFERENCES sessions(id),
    agent_output JSONB,
    run_metadata JSONB,  -- Captured operational metadata for run_metadata evaluators
    status VARCHAR(20) DEFAULT 'pending',
    latency_ms INTEGER,
    token_usage_input INTEGER DEFAULT 0,
    token_usage_output INTEGER DEFAULT 0,
    cost DECIMAL(10, 6),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Evaluation Scores (per evaluator per result)
CREATE TABLE evaluation_scores (
    id SERIAL PRIMARY KEY,
    result_id INTEGER REFERENCES evaluation_results(id) ON DELETE CASCADE,
    evaluator_id INTEGER REFERENCES evaluators(id),
    score DECIMAL(5, 4),  -- 0.0000 to 1.0000
    passed BOOLEAN,
    feedback TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_dataset_examples_dataset ON dataset_examples(dataset_id);
CREATE INDEX idx_evaluation_runs_dataset ON evaluation_runs(dataset_id);
CREATE INDEX idx_evaluation_runs_agent ON evaluation_runs(agent_id);
CREATE INDEX idx_evaluation_runs_status ON evaluation_runs(status);
CREATE INDEX idx_evaluation_results_run ON evaluation_results(run_id);
CREATE INDEX idx_evaluation_results_status ON evaluation_results(status);
CREATE INDEX idx_evaluation_scores_result ON evaluation_scores(result_id);
```

---

## API Endpoints

### Datasets

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/datasets` | List datasets with pagination, filtering |
| POST | `/api/v1/datasets` | Create new dataset |
| GET | `/api/v1/datasets/{id}` | Get dataset details |
| PUT | `/api/v1/datasets/{id}` | Update dataset |
| DELETE | `/api/v1/datasets/{id}` | Delete dataset |
| POST | `/api/v1/datasets/{id}/import` | Import examples from CSV/JSON |
| GET | `/api/v1/datasets/{id}/export` | Export dataset as CSV/JSON |

### Dataset Examples

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/datasets/{id}/examples` | List examples with pagination |
| POST | `/api/v1/datasets/{id}/examples` | Create single example |
| POST | `/api/v1/datasets/{id}/examples/batch` | Create multiple examples |
| GET | `/api/v1/datasets/{id}/examples/{eid}` | Get example details |
| PUT | `/api/v1/datasets/{id}/examples/{eid}` | Update example |
| DELETE | `/api/v1/datasets/{id}/examples/{eid}` | Delete example |

### Evaluators

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/evaluators` | List evaluators (builtin + user) |
| POST | `/api/v1/evaluators` | Create custom evaluator |
| GET | `/api/v1/evaluators/{id}` | Get evaluator details |
| PUT | `/api/v1/evaluators/{id}` | Update evaluator |
| DELETE | `/api/v1/evaluators/{id}` | Delete evaluator |
| POST | `/api/v1/evaluators/{id}/test` | Test evaluator with sample data |

### Evaluation Runs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/evaluations` | List runs with filtering |
| POST | `/api/v1/evaluations` | Start new evaluation run |
| GET | `/api/v1/evaluations/{id}` | Get run details with metrics |
| DELETE | `/api/v1/evaluations/{id}` | Delete run |
| POST | `/api/v1/evaluations/{id}/cancel` | Cancel running evaluation |
| POST | `/api/v1/evaluations/{id}/retry-failed` | Retry failed examples |
| GET | `/api/v1/evaluations/{id}/results` | Get results with pagination |
| GET | `/api/v1/evaluations/{id}/results/{rid}` | Get single result with scores |
| GET | `/api/v1/evaluations/compare` | Compare multiple runs |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `/api/v1/ws/evaluations/{id}` | Real-time run progress updates |

---

## Built-in Evaluators

### 1. Exact Match
```json
{
  "name": "Exact Match",
  "type": "exact_match",
  "description": "Checks if agent output exactly matches expected output",
  "config": {
    "case_sensitive": true,
    "strip_whitespace": true,
    "normalize_unicode": false
  }
}
```

### 2. Contains
```json
{
  "name": "Contains Expected",
  "type": "contains",
  "description": "Checks if agent output contains the expected output",
  "config": {
    "case_sensitive": false
  }
}
```

### 3. JSON Match
```json
{
  "name": "JSON Structure Match",
  "type": "json_match",
  "description": "Compares JSON structures with configurable matching",
  "config": {
    "ignore_order": true,
    "subset_match": false,
    "ignore_extra_keys": false
  }
}
```

### 4. Semantic Similarity
```json
{
  "name": "Semantic Similarity",
  "type": "semantic_similarity",
  "description": "Uses embeddings to measure semantic similarity",
  "config": {
    "threshold": 0.85,
    "model": "text-embedding-3-small"
  }
}
```

### 5. LLM Judge - Correctness
```json
{
  "name": "LLM Judge - Correctness",
  "type": "llm_judge",
  "description": "Uses an LLM to evaluate if the output is correct",
  "config": {
    "model": "gpt-4o-mini",
    "criteria": "correctness",
    "prompt_template": "You are evaluating an AI assistant's response.\n\nInput: {input}\nExpected Output: {expected_output}\nActual Output: {actual_output}\n\nEvaluate if the actual output is correct and complete. Consider:\n1. Does it answer the question/task correctly?\n2. Is the information accurate?\n3. Is anything important missing?\n\nRespond with a JSON object:\n{\n  \"score\": <0.0-1.0>,\n  \"passed\": <true/false>,\n  \"reasoning\": \"<explanation>\"\n}"
  }
}
```

### 6. LLM Judge - Helpfulness
```json
{
  "name": "LLM Judge - Helpfulness",
  "type": "llm_judge",
  "description": "Uses an LLM to evaluate helpfulness",
  "config": {
    "model": "gpt-4o-mini",
    "criteria": "helpfulness",
    "prompt_template": "..."
  }
}
```

### 7. LLM Judge - Safety
```json
{
  "name": "LLM Judge - Safety",
  "type": "llm_judge",
  "description": "Checks for harmful or inappropriate content",
  "config": {
    "model": "gpt-4o-mini",
    "criteria": "safety",
    "prompt_template": "..."
  }
}
```

### 8. Regex Match
```json
{
  "name": "Regex Pattern Match",
  "type": "regex_match",
  "category": "output",
  "description": "Checks if output matches a regex pattern",
  "config": {
    "use_expected_as_pattern": true,
    "flags": ["IGNORECASE", "MULTILINE"]
  }
}
```

---

## Built-in Run Metadata Evaluators

### 9. Token Efficiency
```json
{
  "name": "Token Efficiency",
  "type": "token_efficiency",
  "category": "run_metadata",
  "description": "Evaluates if the agent used tokens efficiently relative to output",
  "config": {
    "max_input_tokens": 5000,
    "max_output_tokens": 2000,
    "max_total_tokens": 7000,
    "efficiency_mode": "total"
  }
}
```

**Scoring Logic:**
- Score = 1.0 if under thresholds
- Score decreases proportionally as tokens exceed thresholds
- `efficiency_mode`: "total" | "input" | "output" | "ratio" (output/input)

### 10. Latency Threshold
```json
{
  "name": "Latency Threshold",
  "type": "latency_threshold",
  "category": "run_metadata",
  "description": "Checks if response time is within acceptable limits",
  "config": {
    "max_ms": 30000,
    "warning_ms": 15000
  }
}
```

**Scoring Logic:**
- Score = 1.0 if latency <= warning_ms
- Score = 0.5 if warning_ms < latency <= max_ms
- Score = 0.0 if latency > max_ms

### 11. Cost Threshold
```json
{
  "name": "Cost Threshold",
  "type": "cost_threshold",
  "category": "run_metadata",
  "description": "Checks if execution cost is within budget",
  "config": {
    "max_cost_usd": 0.10,
    "warning_cost_usd": 0.05
  }
}
```

### 12. Chain Length
```json
{
  "name": "Chain Length",
  "type": "chain_length",
  "category": "run_metadata",
  "description": "Evaluates if agent completed task in reasonable number of steps",
  "config": {
    "max_steps": 10,
    "warning_steps": 5,
    "optimal_steps": null
  }
}
```

**Scoring Logic:**
- If `optimal_steps` set: Score based on distance from optimal
- Otherwise: Score = 1.0 if <= warning_steps, decreases to 0 at max_steps

### 13. Tool Call Success Rate
```json
{
  "name": "Tool Call Success Rate",
  "type": "tool_call_success_rate",
  "category": "run_metadata",
  "description": "Percentage of tool calls that succeeded without errors",
  "config": {
    "min_success_rate": 0.9,
    "ignore_tools": []
  }
}
```

**Scoring Logic:**
- Score = successful_calls / total_calls
- Pass if score >= min_success_rate

### 14. Tool Selection
```json
{
  "name": "Tool Selection",
  "type": "tool_selection",
  "category": "run_metadata",
  "description": "Evaluates if agent used appropriate tools for the task",
  "config": {
    "required_tools": [],
    "forbidden_tools": [],
    "preferred_tools": [],
    "mode": "flexible"
  }
}
```

**Modes:**
- `strict`: Must use exactly required_tools, no others
- `required`: Must use all required_tools, may use others
- `flexible`: Preferred_tools give bonus, forbidden_tools give penalty
- `forbidden_only`: Only penalize for using forbidden_tools

**Scoring Logic:**
- `strict`: 1.0 if exact match, 0.0 otherwise
- `required`: 1.0 if all required used, 0.0 if any missing
- `flexible`: Base 0.5, +0.1 per preferred used, -0.2 per forbidden used
- `forbidden_only`: 1.0 - (0.25 * forbidden_count)

### 15. Error Rate
```json
{
  "name": "Error Rate",
  "type": "error_rate",
  "category": "run_metadata",
  "description": "Evaluates errors and retries during execution",
  "config": {
    "max_errors": 2,
    "max_retries": 3,
    "count_warnings": false
  }
}
```

**Scoring Logic:**
- Score = 1.0 - (errors / max_errors) - (retries / max_retries)
- Minimum score = 0.0

### 16. Span Count
```json
{
  "name": "Span Count",
  "type": "span_count",
  "category": "run_metadata",
  "description": "Evaluates total span count and distribution",
  "config": {
    "max_total_spans": 50,
    "max_llm_spans": 10,
    "max_tool_spans": 20
  }
}
```

### 17. Custom Metadata Evaluator
```json
{
  "name": "Custom Metadata Evaluator",
  "type": "custom_metadata",
  "category": "run_metadata",
  "description": "User-defined Python function to evaluate run metadata",
  "config": {
    "function_code": "def evaluate(input, expected_output, actual_output, run_metadata):\n    # Custom evaluation logic\n    return {'score': 1.0, 'passed': True, 'feedback': ''}"
  }
}
```

---

## Frontend Pages

### 1. Datasets Page (`/datasets`)

**Layout:** Grid/list view of evaluation datasets

**Features:**
- Dataset cards showing name, description, example count, tags
- Create new dataset button
- Search and filter by tags
- Quick actions: View, Edit, Run Evaluation, Delete

**Components:**
- `DatasetCard` - Dataset summary card
- `DatasetListItem` - List view row
- `CreateDatasetDialog` - Quick create modal

### 2. Dataset Editor Page (`/datasets/:id`)

**Layout:** Split view - dataset info on left, examples table on right

**Left Panel:**
- Dataset name, description editor
- Schema type selector (text/structured)
- JSON schema editors (if structured)
- Tags input
- Save/Cancel buttons

**Right Panel (Examples Table):**
- Paginated table of examples
- Columns: Name, Input (truncated), Expected Output (truncated), Tags, Actions
- Inline expand to see full content
- Add example button (opens form/modal)
- Bulk import button (CSV/JSON upload)
- Bulk delete selected
- Search/filter examples

**Components:**
- `DatasetForm` - Dataset metadata form
- `ExamplesTable` - Paginated examples list
- `ExampleForm` - Create/edit example form
- `ImportExamplesDialog` - File upload and mapping
- `ExampleDetailPanel` - Expanded example view

### 3. Evaluators Page (`/evaluators`)

**Layout:** List of available evaluators

**Features:**
- Built-in evaluators section (read-only, clone to customize)
- Custom evaluators section
- Create custom evaluator button
- Test evaluator with sample data

**Components:**
- `EvaluatorCard` - Evaluator summary
- `EvaluatorForm` - Create/edit custom evaluator
- `EvaluatorTestPanel` - Test with sample input/output

### 4. Evaluator Editor Page (`/evaluators/:id`)

**Layout:** Form-based editor

**Features:**
- Type selector with configuration options
- For `custom_code`: Monaco editor for Python function
- For `llm_judge`: Prompt template editor with variable highlighting
- Test panel to try evaluator

### 5. Evaluation Runs Page (`/evaluations`)

**Layout:** List of evaluation runs with filtering

**Features:**
- Run cards/list showing: name, dataset, agent, status, pass rate, date
- Filter by: dataset, agent, status, date range
- Quick compare checkbox selection
- "Compare Selected" button

**Components:**
- `EvaluationRunCard` - Run summary with progress/metrics
- `RunFilters` - Filter controls
- `CompareButton` - Opens comparison view

### 6. New Evaluation Dialog/Page (`/evaluations/new`)

**Layout:** Wizard or single-page form

**Steps/Sections:**
1. Select dataset
2. Select agent (and optionally specific version)
3. Select evaluators (multi-select with descriptions)
4. Configure run options (concurrency, timeout, sample size)
5. Review and start

**Components:**
- `DatasetSelector` - Searchable dataset picker
- `AgentSelector` - Agent picker with version dropdown
- `EvaluatorSelector` - Multi-select evaluator list
- `RunConfigForm` - Advanced options

### 7. Evaluation Run Detail Page (`/evaluations/:id`)

**Layout:** Dashboard with results

**Header:**
- Run name, status badge, progress bar (if running)
- Dataset and agent links
- Quick stats: Pass rate, Avg score, Total cost, Duration
- Actions: Cancel (if running), Retry Failed, Export Results

**Tabs:**
1. **Overview** - High-level metrics and charts
2. **Results** - Per-example results table
3. **Run Metrics** - Operational/run metadata analysis

**Overview Tab:**
- Score distribution chart (histogram)
- Pass/fail pie chart
- Per-evaluator breakdown table (grouped by category: Output vs Run Metadata)
- Tag breakdown table (if examples have tags)

**Results Tab:**
- Paginated list of results
- Columns: Example, Status, Agent Output (truncated), Score, Latency, Tool Calls, Actions
- Expandable rows for full detail
- Filter by: status (pass/fail/error), evaluator, score range
- Click row to open detail panel

**Run Metrics Tab:**
- **Token Usage Analysis**
  - Distribution chart (input vs output tokens)
  - Efficiency scatter plot
  - Top token consumers
- **Tool Usage Analysis**
  - Tools used distribution (bar chart)
  - Tool success rate by tool (bar chart with success/fail stacked)
  - Tool call timeline
- **Chain Length Analysis**
  - Distribution histogram
  - Correlation with pass/fail
- **Latency Analysis**
  - Distribution histogram
  - Latency vs chain length scatter
- **Cost Breakdown**
  - Per-model costs
  - Cost vs score correlation

**Detail Panel (slide-out or modal):**
- Full input display
- Expected output display
- Agent output display (with diff highlighting option)
- All evaluator scores with feedback (grouped by category)
- Run metadata summary (tokens, tools used, chain length, etc.)
- Link to full session trace

**Components:**
- `RunHeader` - Status, progress, quick actions
- `RunOverviewTab` - Charts and output evaluator statistics
- `RunResultsTab` - Paginated results table
- `RunMetricsTab` - Operational metrics visualizations
- `ResultDetailPanel` - Full result view with metadata
- `ScoreChart` - Score distribution visualization
- `EvaluatorBreakdown` - Per-evaluator stats (grouped by category)
- `TokenUsageChart` - Token analysis visualizations
- `ToolUsageChart` - Tool usage visualizations
- `ChainLengthChart` - Chain length distribution

### 8. Comparison Page (`/evaluations/compare?runs=1,2,3`)

**Layout:** Side-by-side comparison

**Features:**
- Compare 2-4 runs simultaneously
- Overall metrics comparison table
- Per-example comparison (same example across runs)
- Highlight differences in scores
- Identify regressions and improvements

**Components:**
- `ComparisonHeader` - Run selectors
- `MetricsComparison` - Side-by-side metrics table
- `ExampleComparison` - Per-example breakdown

---

## Implementation Phases

### Phase 1: Database & Core Backend ✅ COMPLETE

**Deliverables:**
- Database migrations for all tables
- SQLAlchemy models
- Pydantic schemas
- Basic CRUD services for datasets, examples, evaluators

**Files Created:**
- `alembic/versions/a1b2c3d4e5f6_add_evaluation_tables.py`
- `app/models/evaluation.py`
- `app/schemas/evaluation.py`
- `app/services/dataset_service.py`
- `app/services/evaluator_service.py`

### Phase 2: Evaluator Engine ✅ COMPLETE

**Deliverables:**
- Evaluator execution engine
- Built-in evaluator implementations (17 evaluators in single file)
- Factory pattern with registry
- Placeholder implementations for LLM Judge, Semantic Similarity, Custom Code

**Files Created:**
- `app/services/evaluator_engine.py` - All evaluator implementations

### Phase 3: Evaluation Runner ✅ COMPLETE

**Deliverables:**
- Evaluation run orchestrator
- Async execution with concurrency control
- Progress tracking and status updates
- Metrics aggregation
- WebSocket progress callbacks (ready for integration)

**Files Created:**
- `app/services/evaluation_runner.py`

### Phase 4: REST API ✅ COMPLETE

**Deliverables:**
- All dataset endpoints
- All example endpoints
- All evaluator endpoints
- All run endpoints
- Import/export functionality

**Files Created:**
- `app/api/v1/evaluations.py` - 24 endpoints covering all operations

### Phase 5: Frontend - Datasets 🔲 NOT STARTED

**Deliverables:**
- Datasets list page with grid/list view
- Dataset editor page with split layout
- Examples table with CRUD, pagination, search
- Import/export UI (CSV/JSON)

**Files to Create:**
- `frontend/src/pages/DatasetsPage.tsx`
- `frontend/src/pages/DatasetEditorPage.tsx`
- `frontend/src/components/datasets/DatasetCard.tsx`
- `frontend/src/components/datasets/DatasetForm.tsx`
- `frontend/src/components/datasets/ExamplesTable.tsx`
- `frontend/src/components/datasets/ExampleForm.tsx`
- `frontend/src/components/datasets/ImportExamplesDialog.tsx`
- `frontend/src/api/hooks/useDatasets.ts`

### Phase 6: Frontend - Evaluators 🔲 NOT STARTED

**Deliverables:**
- Evaluators list page (built-in + custom sections)
- Evaluator editor page with type-specific config
- Test evaluator panel
- Clone evaluator functionality

**Files to Create:**
- `frontend/src/pages/EvaluatorsPage.tsx`
- `frontend/src/pages/EvaluatorEditorPage.tsx`
- `frontend/src/components/evaluators/EvaluatorCard.tsx`
- `frontend/src/components/evaluators/EvaluatorForm.tsx`
- `frontend/src/components/evaluators/EvaluatorTestPanel.tsx`
- `frontend/src/api/hooks/useEvaluators.ts`

### Phase 7: Frontend - Evaluation Runs 🔲 NOT STARTED

**Deliverables:**
- Runs list page with filtering
- New evaluation wizard (dataset → agent → evaluators → config)
- Run detail page with Overview, Results, Run Metrics tabs
- Real-time progress via WebSocket
- Results visualization (charts, tables)

**Files to Create:**
- `frontend/src/pages/EvaluationsPage.tsx`
- `frontend/src/pages/EvaluationRunPage.tsx`
- `frontend/src/pages/NewEvaluationPage.tsx`
- `frontend/src/components/evaluations/RunCard.tsx`
- `frontend/src/components/evaluations/RunOverviewTab.tsx`
- `frontend/src/components/evaluations/RunResultsTab.tsx`
- `frontend/src/components/evaluations/RunMetricsTab.tsx`
- `frontend/src/components/evaluations/ResultDetailPanel.tsx`
- `frontend/src/api/hooks/useEvaluations.ts`

### Phase 8: Comparison & Polish 🔲 NOT STARTED

**Deliverables:**
- Comparison page (2-4 runs side-by-side)
- Export results functionality
- Error handling and edge cases
- Loading states and skeletons
- Accessibility review

**Files to Create:**
- `frontend/src/pages/EvaluationComparePage.tsx`
- `frontend/src/components/evaluations/MetricsComparison.tsx`
- `frontend/src/components/evaluations/ExampleComparison.tsx`
- Various polish across all components

---

## User Flows

### Flow 1: Create Dataset and Add Examples

1. User navigates to `/datasets`
2. Clicks "New Dataset"
3. Enters name, description, selects schema type
4. Saves dataset, redirected to editor
5. Clicks "Add Example"
6. Enters input and expected output
7. Saves example, sees it in table
8. Optionally imports more from CSV

### Flow 2: Run an Evaluation

1. User navigates to `/evaluations`
2. Clicks "New Evaluation"
3. Selects dataset from dropdown (sees example count)
4. Selects agent (sees tool list)
5. Checks desired evaluators (Exact Match, LLM Judge)
6. Adjusts concurrency if needed
7. Clicks "Start Evaluation"
8. Sees real-time progress as examples complete
9. Views results when done

### Flow 3: Analyze Results

1. User opens completed run from list
2. Sees overall pass rate (75%) and score distribution
3. Filters results to show only failures
4. Clicks on a failed result
5. Sees expected vs actual output side-by-side
6. Reads LLM judge feedback explaining the issue
7. Clicks "View Session" to see full trace
8. Identifies issue in agent's tool usage

### Flow 4: Compare Agent Versions

1. User has two runs: v1 and v2 of same agent
2. Selects both runs with checkboxes
3. Clicks "Compare Selected"
4. Sees side-by-side metrics: v2 has 10% higher pass rate
5. Scrolls to per-example comparison
6. Identifies which examples improved/regressed
7. Decides v2 is ready to deploy

---

## Technical Considerations

### Evaluation Execution

- Evaluations run as background tasks (Celery or asyncio)
- Configurable concurrency to avoid rate limits
- Each example creates a full agent session for traceability
- Results are saved incrementally (not all at once at end)
- WebSocket broadcasts progress updates

### LLM Judge Implementation

- Uses configurable model (default: gpt-4o-mini for cost)
- Structured output parsing for score extraction
- Fallback handling if LLM response is malformed
- Caches embeddings for semantic similarity

### Custom Code Evaluator

- Runs in sandboxed environment (RestrictedPython or subprocess)
- Function signature: `def evaluate(input, expected_output, actual_output) -> dict`
- Must return: `{"score": float, "passed": bool, "feedback": str}`
- Timeout per evaluation (5 seconds default)

### Performance

- Large datasets: pagination everywhere, lazy loading
- Results table: virtual scrolling for 1000+ results
- Metrics: pre-computed and cached on run record
- Background recalculation if scores change

---

## Security Considerations

- Datasets owned by users, not shared (unless future sharing feature)
- Custom code evaluators run sandboxed
- LLM judge prompts should not leak sensitive data
- Rate limiting on evaluation runs to prevent abuse

---

## Future Enhancements (Out of Scope)

1. **Dataset Sharing**: Share datasets between users/teams
2. **Scheduled Evaluations**: Run evaluations on schedule (daily regression tests)
3. **CI/CD Integration**: API for running evaluations in pipelines
4. **Golden Dataset Generation**: Auto-generate examples from successful sessions
5. **A/B Testing Integration**: Link evaluations to prompt A/B tests
6. **Multi-turn Conversations**: Datasets with conversation flows, not just single turns
7. **Human Evaluation**: UI for human labelers to score results
8. **Evaluation Templates**: Pre-built datasets for common use cases

---

## Success Metrics

1. **Adoption**: % of users who create at least one dataset
2. **Usage**: Average evaluations run per user per week
3. **Value**: Users who run evaluations have higher agent quality scores
4. **Performance**: 95th percentile evaluation completion time under 5 minutes for 100 examples

---

## Appendix A: Example Dataset Import Formats

### CSV Format
```csv
name,input,expected_output,tags
"Greeting","Hello, how are you?","I'm doing well, thank you for asking!","easy,greeting"
"Math","What is 2+2?","4","easy,math"
```

### JSON Format
```json
{
  "examples": [
    {
      "name": "Greeting",
      "input": "Hello, how are you?",
      "expected_output": "I'm doing well, thank you for asking!",
      "tags": ["easy", "greeting"]
    },
    {
      "name": "Math",
      "input": "What is 2+2?",
      "expected_output": "4",
      "tags": ["easy", "math"]
    }
  ]
}
```

---

## Appendix B: Custom Output Evaluator Example

```python
def evaluate(input: str, expected_output: str, actual_output: str) -> dict:
    """
    Custom evaluator that checks if the output contains all keywords
    from the expected output.
    """
    expected_keywords = set(expected_output.lower().split())
    actual_lower = actual_output.lower()

    found = sum(1 for kw in expected_keywords if kw in actual_lower)
    total = len(expected_keywords)

    score = found / total if total > 0 else 0.0
    passed = score >= 0.8

    missing = [kw for kw in expected_keywords if kw not in actual_lower]

    return {
        "score": score,
        "passed": passed,
        "feedback": f"Found {found}/{total} keywords. Missing: {missing}" if missing else "All keywords found."
    }
```

---

## Appendix B2: Custom Run Metadata Evaluator Example

```python
def evaluate(input: str, expected_output: str, actual_output: str, run_metadata: dict) -> dict:
    """
    Custom evaluator that checks operational efficiency:
    - Must use web_search tool for research questions
    - Should not exceed 5 tool calls
    - Should not retry more than once
    """
    issues = []
    score = 1.0

    # Check if this looks like a research question
    research_keywords = ['search', 'find', 'what is', 'who is', 'latest', 'news']
    is_research = any(kw in input.lower() for kw in research_keywords)

    tools_used = run_metadata.get('tool_calls', {}).get('tools_used', [])
    total_tool_calls = run_metadata.get('tool_calls', {}).get('total', 0)
    failed_calls = run_metadata.get('tool_calls', {}).get('failed', 0)
    retries = run_metadata.get('retries', 0)

    # Check tool selection for research questions
    if is_research and 'web_search' not in tools_used:
        score -= 0.3
        issues.append("Research question but web_search not used")

    # Check tool call count
    if total_tool_calls > 5:
        score -= 0.2
        issues.append(f"Too many tool calls: {total_tool_calls} (max 5)")

    # Check for excessive retries
    if retries > 1:
        score -= 0.2
        issues.append(f"Too many retries: {retries}")

    # Check for failed tool calls
    if failed_calls > 0:
        score -= 0.1 * failed_calls
        issues.append(f"Failed tool calls: {failed_calls}")

    score = max(0.0, score)
    passed = score >= 0.7

    return {
        "score": score,
        "passed": passed,
        "feedback": "; ".join(issues) if issues else "All operational checks passed."
    }
```

---

## Appendix B3: Tool Selection Evaluator with Expected Tools

For dataset examples that require specific tools, you can store the expected tools in the example metadata:

**Dataset Example:**
```json
{
  "input": "Search for the latest news about AI and save a summary to a file",
  "expected_output": "I've searched for AI news and saved the summary to ai_news.txt",
  "metadata": {
    "expected_tools": ["web_search", "file_write"],
    "forbidden_tools": ["python_exec"],
    "category": "research_and_save"
  }
}
```

**Custom Evaluator Using Example Metadata:**
```python
def evaluate(input: str, expected_output: str, actual_output: str, run_metadata: dict) -> dict:
    """
    Evaluates tool selection against expected tools defined in example metadata.
    Note: Example metadata is available in run_metadata['example_metadata']
    """
    example_meta = run_metadata.get('example_metadata', {})
    expected_tools = set(example_meta.get('expected_tools', []))
    forbidden_tools = set(example_meta.get('forbidden_tools', []))

    tools_used = set(run_metadata.get('tool_calls', {}).get('tools_used', []))

    issues = []
    score = 1.0

    # Check for missing required tools
    missing = expected_tools - tools_used
    if missing:
        score -= 0.3 * len(missing)
        issues.append(f"Missing expected tools: {list(missing)}")

    # Check for forbidden tools
    used_forbidden = tools_used & forbidden_tools
    if used_forbidden:
        score -= 0.4 * len(used_forbidden)
        issues.append(f"Used forbidden tools: {list(used_forbidden)}")

    score = max(0.0, score)
    passed = score >= 0.7 and len(used_forbidden) == 0

    return {
        "score": score,
        "passed": passed,
        "feedback": "; ".join(issues) if issues else f"Correctly used tools: {list(tools_used)}"
    }
```

---

## Appendix C: LLM Judge Prompt Template Variables

Available variables for prompt templates:

| Variable | Description |
|----------|-------------|
| `{input}` | The input sent to the agent |
| `{expected_output}` | The expected/ground truth output |
| `{actual_output}` | The agent's actual output |
| `{context}` | Optional context from the example |
| `{metadata}` | Example metadata as JSON |
| `{run_metadata}` | Run operational metadata (tokens, tools, latency, etc.) |
| `{tools_used}` | List of tools used during execution |
| `{chain_length}` | Number of agent iterations |
| `{latency_ms}` | Total execution time in milliseconds |
| `{token_count}` | Total tokens used |

**Example LLM Judge for Operational Efficiency:**
```
You are evaluating an AI agent's operational efficiency.

Input: {input}
Output: {actual_output}

Operational Metrics:
- Tools used: {tools_used}
- Chain length: {chain_length} iterations
- Latency: {latency_ms}ms
- Tokens used: {token_count}

Evaluate the agent's efficiency:
1. Did it use appropriate tools for the task?
2. Was the chain length reasonable (typically 1-5 iterations)?
3. Was the response time acceptable?

Respond with JSON: {"score": 0.0-1.0, "passed": true/false, "reasoning": "..."}
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-08 | Claude | Initial specification |
| 1.1 | 2026-01-08 | Claude | Added implementation progress tracking, marked Phases 1-4 complete |
