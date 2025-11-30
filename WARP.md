# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This repository contains sample agents for the ERC3: AI Agents in Action competition. Agents connect to the ERC3 platform to solve benchmarks (currently focused on the "store" benchmark - an e-commerce simulation).

**Architecture**: Agents use the ERC3 SDK to interact with benchmarks via API, employing LLMs (primarily OpenAI GPT-4o) to reason through tasks. The sgr-agent-store implementation uses Schema-Guided Reasoning (SGR) with Pydantic structured outputs for adaptive decision-making in a single recursive prompt loop.

## Environment Setup

Required environment variables:
- `ERC3_API_KEY` - Competition API key (get from https://erc.timetoact-group.at/)
- `OPENAI_API_KEY` - OpenAI API key for LLM access (or equivalent for other providers)

Set up a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## Development Commands

### Running an Agent

Navigate to an agent directory and install dependencies:
```bash
cd sgr-agent-store
pip install -r requirements.txt
python3 main.py
```

### Testing Individual Components

To test store API interactions without running full agent:
```python
from erc3 import ERC3, store

core = ERC3()
res = core.start_session(benchmark="store", workspace="your-workspace", name="Test Session")
# Use core.get_store_client() for store interactions
```

## Code Architecture

### Session & Task Flow

1. **Session Creation**: `core.start_session()` initializes a benchmark session with metadata (benchmark type, workspace, agent name, architecture)
2. **Task Iteration**: Each session contains multiple tasks retrieved via `core.session_status()`
3. **Task Execution**: 
   - `core.start_task()` begins a task
   - Agent executes reasoning/action loop
   - `core.complete_task()` finalizes and evaluates the task
4. **Session Completion**: `core.submit_session()` submits results to the platform

### Agent Pattern (SGR Implementation)

The sgr-agent-store uses a structured reasoning loop:

1. **Conversation Context**: Maintains a message log with system prompt and task description
2. **Reasoning Step**: LLM generates `NextStep` (structured output) containing:
   - Current state assessment
   - Remaining plan steps
   - Task completion status
   - Next function/tool to execute
3. **Tool Dispatch**: The chosen tool (e.g., `ListProducts`, `AddProductToBasket`) is dispatched to the store API
4. **Result Integration**: API response is appended to conversation history
5. **Loop**: Repeat until agent returns `ReportTaskCompletion`

### Key Components

**ERC3 SDK Integration**:
- `ERC3()` - Core API client for session management
- `api.get_store_client(task)` - Returns store-specific API client
- `api.log_llm()` - Logs LLM usage for tracking
- `store_api.dispatch()` - Executes store operations

**Store Benchmark Tools** (via `erc3.store`):
- `Req_ListProducts` - Browse products (with pagination)
- `Req_ViewBasket` - Check basket contents and totals
- `Req_AddProductToBasket` / `Req_RemoveItemFromBasket` - Manage cart
- `Req_ApplyCoupon` / `Req_RemoveCoupon` - Handle discounts (one at a time)
- `Req_CheckoutBasket` - Complete purchase

**SGR Pattern**:
- Uses OpenAI's structured outputs (`client.beta.chat.completions.parse()`)
- Pydantic models define tool schemas and routing
- Single recursive prompt handles planning and execution
- Tool calls are serialized as OpenAI-style function calls in conversation history

### Project Structure

- `sgr-agent-store/` - Reference implementation using Schema-Guided Reasoning
  - `main.py` - Session orchestration and task loop
  - `store_agent.py` - Agent reasoning logic with SGR pattern
  - `requirements.txt` - Dependencies (erc3, openai, kibernikto)
- `kibernikto-store/` - Stub/skeleton for new agent implementations
- `res/` - Screenshots and documentation assets

## Dependencies

Install from custom index (includes ERC3 SDK):
```bash
pip install -r requirements.txt
```

Core dependencies:
- `erc3>=1.0.4` - Competition SDK (from https://erc.timetoact-group.at/)
- `openai>=2.8.1` - OpenAI API client
- `kibernikto` - Schema-Guided Reasoning utilities

## Implementation Notes

- **LLM Logging**: Always call `api.log_llm()` after completions to track usage and costs
- **Pagination**: Store's `ListProducts` returns `NextOffset` when more products exist
- **Coupon Logic**: Only one coupon active at a time; apply new coupon to replace or explicitly remove
- **Error Handling**: Store API raises `ApiException` with `api_error.error` and `detail` fields
- **Safety Limits**: Main loop limited to 30 reasoning steps to prevent runaway execution
- **Max Tokens**: Completions use `max_completion_tokens=16384` for complex reasoning

## Resources

- Competition website: https://www.timetoact-group.at/events/enterprise-rag-challenge-part-3
- Platform & API keys: https://erc.timetoact-group.at/
- Schema-Guided Reasoning: https://abdullin.com/schema-guided-reasoning/
- Discord support: Available via registration email link
