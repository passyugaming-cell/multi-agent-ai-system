# Multi-Agent AI System

A modular, production-oriented Python foundation for a Multi-Agent AI system using the official modern Google GenAI SDK (`google-genai`).

## Target Python Version

- Python 3.11+ (Tested on Python 3.12)

## Project Purpose

This project provides an extensible scaffolding and architectural foundation for specialized AI agents.
Phase 1 establishes clean, typed, and modular abstractions for agents, tools, databases, exception handling, and application configuration.

Planned agent modules in subsequent phases include:
1. **Owner Agent**: High-level task orchestration and decision-making.
2. **CS Agent**: Customer support ticket handling and inquiry processing.
3. **Ads Agent**: Advertising campaign management and marketing analytics.
4. **Debugger Agent**: System diagnostics, error analysis, and automated troubleshooting.

## Project Structure

```
.
├── main.py                 # Application entry point & foundation startup check
├── config.py               # Pydantic settings & Google GenAI client factory
├── requirements.txt        # Project dependencies
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore rules for secrets, caches, and build artifacts
├── README.md               # Project documentation
│
├── agents/                 # Agent modules and placeholder interfaces
│   ├── __init__.py
│   ├── owner_agent.py
│   ├── cs_agent.py
│   ├── ads_agent.py
│   └── debugger_agent.py
│
├── tools/                  # Tool abstractions and security guardrails
│   ├── __init__.py
│   └── base.py             # BaseTool, ToolInput, and ToolOutput definitions
│
├── database/               # Database repository interfaces
│   ├── __init__.py
│   └── base.py             # BaseRepository generic abstract class
│
├── core/                   # Core application models and exceptions
│   ├── __init__.py
│   └── exceptions.py       # Custom exception hierarchy
│
└── tests/                  # Unit test suite
    ├── __init__.py
    └── test_config.py      # Tests for configuration and environment handling
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

Edit `.env` to set your Google API key:

```env
GOOGLE_API_KEY=your_google_api_key_here
ENVIRONMENT=development
LOG_LEVEL=INFO
```

*Note: `GEMINI_API_KEY` is also supported as a fallback credential variable if `GOOGLE_API_KEY` is omitted.*

## How to Run

Run the application entry point:

```bash
python main.py
```

Expected output when running without API keys in Phase 1:

```text
INFO - Initializing Multi-Agent AI System foundation...
INFO - Configuration loaded successfully (Environment: development)
INFO - No API key detected in environment. GenAI client initialization skipped for Phase 1 setup.
INFO - Multi-Agent AI System Phase 1 foundation initialized successfully.
```

## How to Run Tests

Execute the unit test suite with `pytest`:

```bash
pytest
```

## Phase 1 Scope & Limitations

- **Foundation Scaffolding**: Agent classes in `agents/` are structural placeholders without live business logic or fake intelligence.
- **Tools & Database**: Abstract contracts (`BaseTool`, `BaseRepository`) define boundaries without binding to concrete DB engines or allowing arbitrary code execution.
- **SDK Compliance**: Built exclusively with the official modern `google-genai` SDK (`from google import genai`). The legacy `google-generativeai` package is strictly avoided.
