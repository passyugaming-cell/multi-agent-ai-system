# Multi-Agent AI System

A modular, production-oriented Python foundation for a Multi-Agent AI system using the official modern Google GenAI SDK (`google-genai`).

## Target Python Version

- Python 3.11+ (Tested on Python 3.12)

## Project Purpose

This project provides an extensible scaffolding and architectural foundation for specialized AI agents.
Phase 3 implements specialized domain agents (CS Agent, Ads Agent, Debugger Agent), typed inter-agent communication flows, runtime error capture, credential sanitization, and a controlled self-debugging loop.

### Status of Agent Modules
1. **Owner Agent**: High-level task orchestration, decision-support, supervisory routing, and grounded decision modeling (Phase 2 & Phase 3).
2. **CS Agent**: Customer support reasoning, message classification, and grounded customer assistance without hallucinating unavailable business facts (Phase 3).
3. **Ads Agent**: Advertising analytics, campaign performance evaluation, and optimization recommendations without external autonomous action capabilities (Phase 3).
4. **Debugger Agent**: System error classification, root-cause analysis, and structured, non-executing patch recommendations (Phase 3).

## Phase 3 Architecture & Safety Boundaries

```
                         +----------------+
                         |   Owner Agent  |
                         +-------+--------+
                                 |
                +----------------+----------------+
                |                                 |
                v                                 v
        +---------------+                  +---------------+
        |    CS Agent   |                  |    Ads Agent  |
        +-------+-------+                  +-------+-------+
                |                                 |
                |                                 |
                +---------------+-----------------+
                                |
                                v
                       +----------------+
                       | Debugger Agent |
                       +----------------+
                                |
                                v
                       Error Analysis
                                |
                                v
                       Patch Recommendation
```

### Safety Principles & Execution Guardrails
- **The Debugger Agent does NOT automatically modify source code or run shell commands.** All generated patches are structured recommendations requiring human or authorized review (`requires_human_review=True`).
- **The Ads Agent does NOT automatically spend money or perform external campaign actions.** It provides analytics and optimization strategy recommendations only.
- **The CS Agent does NOT invent unavailable business facts.** Product prices, order statuses, inventory, and fees are explicitly marked unavailable when missing from grounded facts.
- **Credential & Secret Sanitization**: `core/debugging/error_capture.py` redacts API keys, bearer tokens, passwords, and secrets before placing stack traces into `ErrorReport` objects for model analysis.
- **Self-Debugging Attempt Limit**: `SelfDebuggingLoop` enforces a strict hard ceiling on debugging iterations (`max_attempts=3`) to prevent infinite recursive error analysis loops.

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
│   ├── ai/                 # Central Google GenAI abstraction
│   │   ├── __init__.py
│   │   ├── exceptions.py   # AI Client exceptions
│   │   └── genai_client.py # GenAIClient wrapper & AIResponse contract
│   └── debugging/          # Runtime error capture and secret sanitization
│       ├── __init__.py
│       └── error_capture.py# capture_exception and sanitize_text
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
│   ├── router.py           # AgentRouter allowlist router
│   ├── owner_agent.py      # OwnerAgent implementation & OwnerDecision schema
│   ├── cs_agent.py         # CSAgent implementation & CSRequest/CSResponse schemas
│   ├── ads_agent.py        # AdsAgent implementation & AdsRequest/AdsAnalysis schemas
│   ├── debugger_agent.py   # DebuggerAgent implementation & DebugAnalysis schema
│   ├── debugging_models.py # ErrorReport, DebuggerRequest, PatchRecommendation
│   ├── debugging_loop.py   # SelfDebuggingLoop orchestration
│   │
│   └── prompts/            # Grounded prompt instructions
│       ├── __init__.py
│       ├── owner_prompt.py # OWNER_SYSTEM_INSTRUCTION
│       ├── cs_prompt.py    # CS_SYSTEM_INSTRUCTION
│       ├── ads_prompt.py   # ADS_SYSTEM_INSTRUCTION
│       └── debugger_prompt.py # DEBUGGER_SYSTEM_INSTRUCTION
│
├── tools/                  # Tool abstractions and security guardrails
│   ├── __init__.py
│   └── base.py             # BaseTool, ToolInput, and ToolOutput definitions
│
├── database/               # Database repository interfaces
│   ├── __init__.py
│   └── base.py             # BaseRepository generic abstract class
│
└── tests/                  # Unit and integration test suite
    ├── __init__.py
    ├── test_config.py           # Tests for configuration and environment handling
    ├── test_genai_client.py     # Tests for GenAIClient (offline mocked)
    ├── test_agent_registry.py   # Tests for AgentRegistry
    ├── test_message_bus.py      # Tests for InMemoryMessageBus
    ├── test_agent_engine.py     # Tests for AgentEngine execution
    ├── test_owner_agent.py      # Tests for OwnerAgent decision logic
    ├── test_cs_agent.py         # Tests for CS Agent reasoning and contracts
    ├── test_ads_agent.py        # Tests for Ads Agent analytics and contracts
    ├── test_debugger_agent.py   # Tests for Debugger Agent analysis and patch recommendations
    ├── test_debugging_loop.py   # Tests for SelfDebuggingLoop and max attempts limit
    ├── test_error_sanitization.py# Tests for credential sanitization and ErrorReport
    └── test_agent_integration.py# End-to-end multi-agent communication integration tests
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

## How to Run Tests

Execute the full unit and integration test suite with `pytest`:

```bash
python3 -m pytest
```

All standard unit and integration tests run completely offline without requiring real API credentials.
