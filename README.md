# Multi-Agent AI System

A modular, production-oriented Python foundation for a Multi-Agent AI system using the official modern Google GenAI SDK (`google-genai`).

## Target Python Version

- Python 3.11+ (Tested on Python 3.12)

## Project Purpose

This project provides an extensible scaffolding and architectural foundation for specialized AI agents.
Phase 2 establishes the core agent execution engine, centralized GenAI client, inter-agent messaging bus, and the Owner Agent.

### Status of Agent Modules
1. **Owner Agent**: High-level task orchestration, decision-support, and grounded decision modeling (Implemented in Phase 2).
2. **CS Agent**: Customer support ticket handling and inquiry processing (Future implementation).
3. **Ads Agent**: Advertising campaign management and marketing analytics (Future implementation).
4. **Debugger Agent**: System diagnostics, error analysis, and automated troubleshooting (Future implementation).

## Project Structure

```
.
├── main.py                 # Application entry point & foundation startup check
├── config.py               # Settings management & GEMINI_MODEL configuration
├── requirements.txt        # Project dependencies
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore rules for secrets, caches, and build artifacts
├── README.md               # Project documentation
│
├── core/                   # Core infrastructure abstractions and exceptions
│   ├── __init__.py
│   ├── exceptions.py       # Custom exception hierarchy
│   └── ai/                 # Central Google GenAI abstraction
│       ├── __init__.py
│       ├── exceptions.py   # AI Client exceptions
│       └── genai_client.py # GenAIClient wrapper & AIResponse contract
│
├── agents/                 # Agent modules, engine, message bus, and contracts
│   ├── __init__.py
│   ├── base.py             # BaseAgent abstract class
│   ├── context.py          # AgentContext execution context
│   ├── contracts.py        # AgentResult execution result model
│   ├── engine.py           # AgentEngine execution orchestrator
│   ├── registry.py         # AgentRegistry in-memory registry
│   ├── messages.py         # AgentMessage and MessageType enum
│   ├── message_bus.py      # MessageBus interface and InMemoryMessageBus
│   ├── owner_agent.py      # OwnerAgent implementation & OwnerDecision schema
│   │
│   └── prompts/            # Grounded prompt instructions
│       ├── __init__.py
│       └── owner_prompt.py # OWNER_SYSTEM_INSTRUCTION prompt
│
├── tools/                  # Tool abstractions and security guardrails
│   ├── __init__.py
│   └── base.py             # BaseTool, ToolInput, and ToolOutput definitions
│
├── database/               # Database repository interfaces
│   ├── __init__.py
│   └── base.py             # BaseRepository generic abstract class
│
└── tests/                  # Unit test suite
    ├── __init__.py
    ├── test_config.py        # Tests for configuration and environment handling
    ├── test_genai_client.py  # Tests for GenAIClient (offline mocked)
    ├── test_agent_registry.py# Tests for AgentRegistry
    ├── test_message_bus.py   # Tests for InMemoryMessageBus
    ├── test_agent_engine.py  # Tests for AgentEngine execution
    └── test_owner_agent.py   # Tests for OwnerAgent decision logic
```

## Setup & Installation

1. Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables:

```bash
cp .env.example .env
```

Edit `.env` to set your Google API key and model choice:

```env
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-2.5-flash
ENVIRONMENT=development
LOG_LEVEL=INFO
```

*Note: `GEMINI_API_KEY` is also supported as a fallback credential variable if `GOOGLE_API_KEY` is omitted.*

## How to Run

Run the application entry point:

```bash
python main.py
```

Expected output when running without API keys:

```text
INFO - Initializing Multi-Agent AI System Phase 2 architecture...
INFO - Configuration loaded successfully (Environment: development, Model: gemini-2.5-flash)
INFO - No API key detected in environment. GenAIClient initialization skipped for bootstrap check.
INFO - Active registered agents in system: []
INFO - Multi-Agent AI System Phase 2 foundation initialized successfully.
```

## How to Run Tests

Execute the full unit test suite with `pytest`:

```bash
python3 -m pytest
```

All standard unit tests run completely offline without requiring real API credentials.

## Phase 2 Implementation Details

- **Centralized GenAI Client**: `GenAIClient` wraps the official `google-genai` SDK (`from google import genai`), managing credentials securely, preventing API key exposure, and sanitizing raw SDK errors into typed application exceptions (`GenAIClientError`, `GenAIModelError`).
- **Agent Framework & Contracts**: `BaseAgent`, `AgentContext`, `AgentResult`, `AgentRegistry`, and `AgentEngine` establish strict typed boundaries and recursion prevention for agent execution.
- **Inter-Agent Messaging**: `InMemoryMessageBus` provides safe, typed pub/sub and request/reply inter-agent communication using validated `AgentMessage` objects.
- **Owner Agent**: `OwnerAgent` leverages grounded system instructions (`OWNER_SYSTEM_INSTRUCTION`) and structured Pydantic model parsing (`OwnerDecision`) for decision support without hallucinating unverified business data.
