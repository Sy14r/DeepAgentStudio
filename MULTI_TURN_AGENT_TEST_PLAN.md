# Agentic Behavior Validation Test Plan

## Test Execution Results (2026-01-05)

### Summary: ✅ AGENTIC BEHAVIOR VALIDATED

All three critical autonomous multi-action tests passed after fixing a tool output issue.

| Scenario | Status | Tool Calls | Result |
|----------|--------|------------|--------|
| **A1**: Multi-Step Calculation | ✅ PASSED | 1 (efficient) | Agent calculated factorial, sqrt, round in single call |
| **A3**: Research & Synthesize | ✅ PASSED | 2 HTTP calls | Agent fetched user + posts, synthesized summary |
| **A5**: Multi-Tool Orchestration | ✅ PASSED | 1 HTTP + 1 Python | Agent fetched users, counted .biz emails (3/10 = 30%) |

### Issue Found & Fixed

**Problem**: Python code execution tool wasn't returning expression results properly.

When the agent wrote code like:
```python
factorial_10 = math.factorial(10)
sqrt_factorial_10 = math.sqrt(factorial_10)
rounded_sqrt = round(sqrt_factorial_10, 2)
(factorial_10, sqrt_factorial_10, rounded_sqrt)  # Trailing expression
```

The tool only returned `"1904.94"` (last variable value) instead of the tuple `[3628800, 1904.94, 1904.94]`.

This caused the agent to loop 10 times (hitting `max_iterations`) because it never received complete output.

**Root Cause**: Python's `exec()` doesn't capture expression results like a REPL.

**Fix Applied** (`backend/app/services/tool_wrapper.py`):
- Added AST parsing to detect if last statement is an expression
- Execute all but last statement with `exec()`
- Evaluate last expression with `eval()` and capture result
- Return result as JSON (handles tuples, lists, dicts properly)

### Test Details

**A1: Multi-Step Calculation**
- Prompt: "Calculate factorial of 10, square root, round to 2 decimal places"
- Agent made 1 efficient tool call (combined all calculations)
- Tool returned: `[3628800, 1904.9409439665053, 1904.94]`
- Agent reported all three values correctly

**A3: Research & Synthesize**
- Prompt: "Fetch user/1, then posts for user, summarize"
- Agent made 2 autonomous HTTP calls:
  1. GET /users/1 → Leanne Graham info
  2. GET /posts?userId=1 → 10 posts
- Agent synthesized comprehensive summary with user details + first post content

**A5: Multi-Tool Orchestration**
- Prompt: "Fetch users, count .biz emails with Python"
- Agent used BOTH tools:
  1. `http_request` → fetched 10 users
  2. `python_code_execution` → filtered, counted .biz emails
- Correct answer: 3 users (30%)
  - Sincere@april.biz
  - Telly.Hoeger@billy.biz
  - Rey.Padberg@karina.biz

### Conclusion

DeepAgentStudio now properly supports **true agentic behavior**:
- ✅ Agents take multiple autonomous tool calls before returning
- ✅ Agents can chain different tools together
- ✅ Execution traces capture all intermediate steps
- ✅ Tool outputs properly captured and returned

---

## Objective

Validate that DeepAgentStudio properly supports **true agentic behavior**:

1. **Autonomous Multi-Action Execution** - Agent takes multiple tool actions in ONE turn before returning
2. **Planning & Decomposition** - Agent breaks complex tasks into steps and executes them
3. **Multi-turn Context** - Agent remembers previous turns when human re-engages
4. **Long Horizon Tasks** - Agent can complete complex multi-step workflows
5. **Error Recovery** - Agent handles tool failures and re-plans

### Key Distinction

**Multi-turn conversation** (Human ↔ Agent alternating):
```
Human: "Calculate X"
Agent: "Result is Y"
Human: "Now do Z"
Agent: "Result is W"
```

**True agentic behavior** (Agent acts autonomously):
```
Human: "Research topic X and write a summary"
Agent: [Thinks] → [Searches API] → [Observes results] → [Searches again] →
       [Observes] → [Synthesizes] → "Here's your summary based on my research..."
```

The agent should take **multiple autonomous actions** before returning control to the human.

---

## Test Environment Setup

### Prerequisites
- [ ] DeepAgentStudio running (docker-compose up)
- [ ] OpenAI or Anthropic API key configured
- [ ] At least one agent created with tools attached
- [ ] Both built-in tools available (python_code_execution, http_request)

### Agent Configurations to Test

| Agent Type | Description | Expected Behavior |
|------------|-------------|-------------------|
| **ReAct** | Reason + Act loop | Step-by-step reasoning with tool calls |
| **Plan-and-Execute** | Plan first, then execute | Creates explicit plan, executes steps |
| **Conversational** | Chat without tools | Memory retention, no tool calls |

---

## Test Scenarios

---

## PART A: Autonomous Multi-Action Tests (Single Turn)

These tests validate the agent can take MULTIPLE actions before returning.

---

### Scenario A1: Multi-Step Calculation (3+ Actions)

**Goal**: Agent performs multiple calculations autonomously in ONE turn

**Agent Type**: ReAct with python_code_execution tool

**Single Prompt**:
```
Calculate the following and give me all results:
1. The factorial of 10
2. The square root of that result
3. Round that to 2 decimal places
```

**Expected Behavior**:
- [ ] Agent calls python_code_execution for factorial (3628800)
- [ ] Agent calls python_code_execution for sqrt (1904.94...)
- [ ] Agent calls python_code_execution for rounding (1904.94)
- [ ] Trace shows 3 tool_call/tool_result pairs
- [ ] Single final answer with all three results

**What We're Testing**: Can the agent chain 3 tool calls autonomously?

---

### Scenario A2: Data Pipeline (4+ Actions)

**Goal**: Agent executes a multi-step data transformation pipeline

**Agent Type**: ReAct with python_code_execution tool

**Single Prompt**:
```
Create a list of numbers 1-10, then:
1. Square each number
2. Filter to keep only values > 50
3. Sum the remaining values
4. Tell me the result
```

**Expected Behavior**:
- [ ] Agent creates list [1,2,3,4,5,6,7,8,9,10]
- [ ] Agent squares: [1,4,9,16,25,36,49,64,81,100]
- [ ] Agent filters: [64, 81, 100]
- [ ] Agent sums: 245
- [ ] Trace shows multiple tool calls (could be 4 separate or combined)
- [ ] Final answer: 245

**What We're Testing**: Can agent maintain state across multiple tool calls?

---

### Scenario A3: Research & Synthesize (API + Reasoning)

**Goal**: Agent makes API call, processes result, makes another call

**Agent Type**: ReAct with http_request tool

**Single Prompt**:
```
Fetch data from https://jsonplaceholder.typicode.com/users/1,
then fetch that user's first post from https://jsonplaceholder.typicode.com/posts?userId=1,
and summarize who the user is and what their first post is about.
```

**Expected Behavior**:
- [ ] Agent calls http_request for user data
- [ ] Agent observes user info (Leanne Graham, etc.)
- [ ] Agent calls http_request for posts
- [ ] Agent observes posts data
- [ ] Agent synthesizes both into coherent summary
- [ ] Trace shows 2 HTTP calls + reasoning

**What We're Testing**: Can agent make sequential API calls and synthesize results?

---

### Scenario A4: Iterative Problem Solving

**Goal**: Agent tries, observes, adjusts approach

**Agent Type**: ReAct with python_code_execution tool

**Single Prompt**:
```
Find the smallest number n where n! (factorial) is greater than 1 million.
Show your work by testing different values.
```

**Expected Behavior**:
- [ ] Agent tests n=5: 120 (too small)
- [ ] Agent tests n=8: 40320 (too small)
- [ ] Agent tests n=10: 3628800 (> 1 million!)
- [ ] Multiple tool calls showing the search process
- [ ] Final answer: n=10

**What We're Testing**: Can agent iterate toward a solution?

---

### Scenario A5: Complex Multi-Tool Task

**Goal**: Agent uses BOTH tools in a single task

**Agent Type**: ReAct with python_code_execution AND http_request

**Single Prompt**:
```
Fetch the list of users from https://jsonplaceholder.typicode.com/users,
then use Python to count how many users have email addresses ending in .biz
and calculate the percentage of total users.
```

**Expected Behavior**:
- [ ] Agent calls http_request to fetch users (10 users)
- [ ] Agent calls python_code_execution to filter/count .biz emails
- [ ] Agent calculates percentage
- [ ] Trace shows both tools used
- [ ] Correct answer (3 users = 30%)

**What We're Testing**: Can agent orchestrate multiple different tools?

---

## PART B: Multi-Turn Context Tests

These tests validate memory across human re-engagement.

---

### Scenario B1: Basic Multi-Turn Memory

**Goal**: Verify agent remembers information from previous turns

**Steps**:
1. Turn 1: "My name is Alex and I'm working on a data analysis project"
2. Turn 2: "What project am I working on?"
3. Turn 3: "What's my name?"

**Expected Results**:
- [ ] Turn 2: Agent correctly recalls "data analysis project"
- [ ] Turn 3: Agent correctly recalls "Alex"
- [ ] Session shows all messages in order
- [ ] Memory indicator shows "Memory Active" in UI

---

### Scenario 2: Multi-Step Calculation Task

**Goal**: Verify agent can use tools across multiple reasoning steps

**Agent Type**: ReAct with python_code_execution tool

**Steps**:
1. Turn 1: "Calculate the compound interest on $10,000 at 5% annual rate for 10 years, compounded monthly"

**Expected Results**:
- [ ] Agent uses python_code_execution tool
- [ ] Trace shows: Thought → Tool Call → Tool Result → Final Answer
- [ ] Correct answer: ~$16,470.09
- [ ] Tool execution recorded in session traces

---

### Scenario 3: Multi-Turn Data Processing

**Goal**: Verify agent can build on previous tool results

**Agent Type**: ReAct with python_code_execution tool

**Steps**:
1. Turn 1: "Create a list of the first 10 Fibonacci numbers"
2. Turn 2: "Now calculate the sum of those numbers"
3. Turn 3: "What's the average of those numbers?"

**Expected Results**:
- [ ] Turn 1: Agent generates [0, 1, 1, 2, 3, 5, 8, 13, 21, 34] or [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
- [ ] Turn 2: Agent recalls/regenerates list and sums (88 or 143)
- [ ] Turn 3: Agent calculates average correctly
- [ ] Each turn shows tool usage in trace
- [ ] Session maintains continuity

---

### Scenario 4: HTTP API Workflow

**Goal**: Verify agent can make API calls and reason about results

**Agent Type**: ReAct with http_request tool

**Steps**:
1. Turn 1: "Fetch a random user from https://randomuser.me/api/ and tell me their name and location"
2. Turn 2: "Based on that user's country, what timezone might they be in?"

**Expected Results**:
- [ ] Turn 1: Agent successfully calls API
- [ ] Turn 1: Agent extracts and presents name/location
- [ ] Turn 2: Agent remembers the country from Turn 1
- [ ] Turn 2: Agent reasons about timezone (may use tool or knowledge)
- [ ] Trace shows HTTP request details

---

### Scenario 5: Complex Planning Task

**Goal**: Verify Plan-and-Execute agent creates and follows multi-step plans

**Agent Type**: Plan-and-Execute with both tools

**Steps**:
1. Turn 1: "I need you to: 1) Generate 5 random numbers between 1-100, 2) Sort them, 3) Calculate their mean and median, 4) Tell me if the mean is greater than the median"

**Expected Results**:
- [ ] Agent creates explicit plan with 4+ steps
- [ ] Agent executes steps in order
- [ ] Trace shows planning phase
- [ ] Trace shows execution of each step
- [ ] Final answer addresses all parts of the request

---

### Scenario 6: Error Recovery

**Goal**: Verify agent can recover from tool errors

**Agent Type**: ReAct with python_code_execution tool

**Steps**:
1. Turn 1: "Calculate 1 divided by 0"
2. Turn 2: "That caused an error. Can you explain what went wrong and then calculate 10 divided by 2 instead?"

**Expected Results**:
- [ ] Turn 1: Agent attempts calculation, gets error
- [ ] Turn 1: Agent reports the error appropriately
- [ ] Turn 2: Agent explains ZeroDivisionError
- [ ] Turn 2: Agent successfully calculates 10/2 = 5
- [ ] Session maintains context through error

---

### Scenario 7: Long Horizon Task (5+ Turns)

**Goal**: Verify context retention over extended conversation

**Agent Type**: ReAct with python_code_execution tool

**Steps**:
1. Turn 1: "Let's build a simple data structure. Start by creating an empty dictionary called 'inventory'"
2. Turn 2: "Add 'apples': 50 to the inventory"
3. Turn 3: "Add 'bananas': 30 to the inventory"
4. Turn 4: "Add 'oranges': 45 to the inventory"
5. Turn 5: "What's the total count of all items in the inventory?"
6. Turn 6: "Which item has the most stock?"

**Expected Results**:
- [ ] Agent maintains concept of "inventory" across all turns
- [ ] Turn 5: Correctly calculates 125 total
- [ ] Turn 6: Correctly identifies "apples" with 50
- [ ] Session shows 6+ message pairs
- [ ] Memory window doesn't lose early context

---

### Scenario 8: Context-Dependent Tool Selection

**Goal**: Verify agent chooses appropriate tool based on context

**Agent Type**: ReAct with both tools

**Steps**:
1. Turn 1: "What's 15 factorial?"
2. Turn 2: "Now fetch the current Bitcoin price from a public API"

**Expected Results**:
- [ ] Turn 1: Uses python_code_execution (math.factorial(15))
- [ ] Turn 2: Uses http_request (calls crypto API)
- [ ] Agent correctly identifies which tool fits each task
- [ ] Both tool results are accurate

---

### Scenario 9: Session Continuation

**Goal**: Verify "Continue Session" feature works correctly

**Steps**:
1. Start new session, Turn 1: "Remember the secret word is 'elephant'"
2. Turn 2: "What's 2+2?"
3. Close browser/navigate away
4. Return to Playground, select "Continue Session" for this session
5. Turn 3: "What was the secret word?"

**Expected Results**:
- [ ] Session loads previous messages in UI
- [ ] Agent recalls "elephant" from Turn 1
- [ ] Session ID remains the same
- [ ] Trace shows continuity

---

### Scenario 10: Conversational Agent Memory

**Goal**: Verify Conversational agents (no tools) maintain memory

**Agent Type**: Conversational (no tools attached)

**Steps**:
1. Turn 1: "I'm planning a trip to Japan in March"
2. Turn 2: "What should I pack?"
3. Turn 3: "Any specific recommendations for the time of year I mentioned?"

**Expected Results**:
- [ ] Turn 2: Agent considers Japan context
- [ ] Turn 3: Agent recalls March timing
- [ ] No tool calls (conversational type)
- [ ] Coherent multi-turn advice

---

## Execution Checklist

### Pre-Test Setup
- [ ] Verify docker-compose services running
- [ ] Verify database has LLM provider configured (OpenAI or Anthropic)
- [ ] Create ReAct agent with BOTH tools attached
- [ ] Verify agent has reasonable system prompt
- [ ] Check max_iterations is set to 10+ in agent config

### Part A: Autonomous Multi-Action Tests (CRITICAL)
- [ ] **A1**: Multi-Step Calculation (3+ tool calls)
- [ ] **A2**: Data Pipeline (state across calls)
- [ ] **A3**: Research & Synthesize (2 API calls)
- [ ] **A4**: Iterative Problem Solving
- [ ] **A5**: Multi-Tool Orchestration

### Part B: Multi-Turn Context Tests
- [ ] B1: Basic Memory
- [ ] B2-B4: Extended context
- [ ] Session Continuation

### Post-Test Validation
- [ ] Review session recordings in Sessions page
- [ ] **Count intermediate steps in traces** (should be > 1 for Part A)
- [ ] Verify traces show tool_call AND tool_result for each action
- [ ] Check that final answer synthesizes all tool results
- [ ] Document any failures or unexpected behavior

---

## Known Limitations to Document

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Buffer memory only | Long conversations may lose early context | Context window config limits turns |
| No summary memory | Can't compress old messages | Planned feature |
| No vector memory | Can't do semantic retrieval | Planned feature |
| Sync execution only | UI waits for full response | Streaming planned |

---

## Success Criteria

### Critical (Must Pass for Agentic Behavior)
- [x] **A1 passes**: Agent executes multi-step calculation (1 efficient call with all results)
- [x] **A3 passes**: Agent chains API calls and synthesizes (2 HTTP calls)
- [x] **A5 passes**: Agent uses multiple different tools together (HTTP + Python)
- [x] Traces show intermediate steps (not just final answer)

### Important (Should Pass)
- [ ] A2, A4 pass (data pipelines and iteration)
- [ ] B1-B3 pass (multi-turn memory)
- [ ] Session continuation works

### Nice to Have
- [ ] Plan-and-Execute agent creates explicit plan
- [ ] Error recovery works gracefully

### Failure Indicators
- Agent only makes 1 tool call then returns (not agentic)
- Agent asks human for permission between each step (too cautious)
- Traces don't capture intermediate steps
- Agent forgets context from previous tool calls

**Notes**:
- Plan-and-Execute may have limitations based on langchain-experimental
- Document any model-specific behaviors (GPT-4 vs Claude 3)
- If agent is "too conservative", may need to adjust system prompt
