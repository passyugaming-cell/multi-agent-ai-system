# Multi-Agent AI System

A production-grade Python Multi-Agent AI System built with the official `google-genai` SDK and Gemini models.

---

## 1. Project Overview

The Multi-Agent AI System is an enterprise-ready architecture designed for coordinated reasoning, specialist task delegation, and automated self-debugging.

- **Owner Agent**: Primary supervisory agent responsible for high-level decision support and delegating requests to specialist agents based on domain intent.
- **Customer Service (CS) Agent**: Specialized reasoning agent for resolving customer inquiries grounded strictly in verified business facts.
- **Ads Agent**: Analytics and optimization advisory agent for campaign metrics (CTR, CPA, ROAS). *Restricted from executing live ad campaign modifications automatically.*
- **Debugger Agent**: Root cause analysis agent that generates non-executing code patch recommendations for runtime failures. *Restricted from executing code or modifying files automatically.*
- **Application Orchestrator**: Coordinates correlation tracking (`request_id`), execution trace logging, security allowlist routing, and error management via the `SelfDebuggingLoop`.
- **GenAI Client Wrapper**: Centralized abstraction for Gemini interaction using the official `google-genai` Python SDK.

---

## 2. Architecture

```
                                USER
                                  │
                                  ▼
                           ┌─────────────┐
                           │  CLI Layer  │
                           └──────┬──────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   Orchestrator  │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   Owner Agent   │
                         └────────┬────────┘
                                  │
                     ┌────────────┴────────────┐
                     │                         │
                     ▼                         ▼
              ┌─────────────┐           ┌─────────────┐
              │  CS Agent   │           │  Ads Agent  │
              └──────┬──────┘           └──────┬──────┘
                     │                         │
                     └────────────┬────────────┘
                                  │
                             errors/failures
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ Debugger Agent  │
                         └────────┬────────┘
                                  │
                                  ▼
                        Self-Debugging Loop
```

### Supporting Infrastructure
- **GenAIClient (`core/ai/genai_client.py`)**: Centralized wrapper for official `google-genai` Gemini SDK calls.
- **AgentEngine (`agents/engine.py`)**: Core execution engine enforcing max recursion depth and execution boundaries.
- **AgentRegistry (`agents/registry.py`)**: In-memory registry storing active agent instances.
- **MessageBus (`agents/message_bus.py`)**: In-memory asynchronous pub/sub and request-reply message bus.
- **SelfDebuggingLoop (`agents/debugging_loop.py`)**: Automated exception capture, secret sanitization, and diagnostic analysis loop.

---

## 3. Requirements

- **Python 3.11+**
- **Git**
- **GitHub account / repository access**
- **Google Gemini API Key** (Required *only* when executing live AI model generation; normal automated tests run offline without calling external APIs).

---

## 4. Clone Repository

```bash
git clone <repository-url>
cd <repository-directory>
```

---

## 5. Create Virtual Environment

### Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows (PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

---

## 6. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 7. Environment Configuration

Copy `.env.example` to create your local `.env` configuration file:

```bash
cp .env.example .env
```

Set required variables inside `.env`:
- `GOOGLE_API_KEY` (or `GEMINI_API_KEY` as fallback): Your Google Gemini API key for live calls.
- `GEMINI_MODEL`: Gemini model identifier (default: `gemini-2.5-flash`).
- `ENVIRONMENT`: Environment mode (e.g. `development`, `production`).
- `LOG_LEVEL`: Logging verbosity (default: `INFO`).

*Note: Never commit `.env` or expose API keys in source code.*

---

## 8. Run Tests

Run the complete test suite offline without requiring an API key:

```bash
pytest
```

Expected result: 100% of tests passing.

---

## 9. Run the Application

### Interactive CLI Mode (Live Gemini API)
```bash
python main.py
```

### Single-Shot Mode (Live Gemini API)
```bash
python main.py "Analyze our advertising campaign ROAS performance."
```

### Deterministic Simulation / Mock Mode (Offline)
Run without requiring a Gemini API key:

```bash
# Interactive mode
python main.py --simulate

# Single-shot mode
python main.py --simulate "Customer asking about refund policy for order #12345"
```

---

## 10. CLI Commands

When running in interactive CLI mode (`python main.py`), the following commands are available:

- `/help` - Display help instructions and list of commands.
- `/status` - Display system status, registered agents count, and message bus configuration.
- `/agents` - List active registered agents and their descriptions.
- `/exit` or `/quit` - Exit interactive CLI mode.

---

## 11. GitHub Codespaces

To run and develop in GitHub Codespaces:

1. Open the repository on GitHub in your web browser.
2. Click the **Code** button, select the **Codespaces** tab, and click **Create codespace on main**.
3. Wait for the cloud environment initialization to finish.
4. Open the integrated terminal and verify the Python version:
   ```bash
   python3 --version
   ```
5. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
6. Run the automated test suite to confirm setup:
   ```bash
   pytest
   ```
7. Run the application in simulation mode:
   ```bash
   python main.py --simulate
   ```

---

## 12. GitHub Actions

Automated CI testing is configured in `.github/workflows/test.yml`.

- **Triggers**: On `push` or `pull_request` to `main` / `master` branches.
- **Environment**: Runner uses `ubuntu-latest` with **Python 3.11**.
- **Execution**: Checks out code, sets up Python, upgrades `pip`, installs `requirements.txt`, and executes `pytest`.
- **Viewing Results**: Results are visible under the **Actions** tab in the GitHub repository.

---

## 13. Troubleshooting

### Python Version Mismatch
- **Issue**: `SyntaxError` or unsupported generic typing syntax.
- **Fix**: Ensure Python 3.11+ is active (`python3 --version`). Use `python3 -m venv .venv` to recreate the virtual environment.

### Dependency Installation Failure
- **Issue**: Errors during `pip install -r requirements.txt`.
- **Fix**: Upgrade pip before installation: `pip install --upgrade pip`.

### Import Error / Module Not Found
- **Issue**: `ModuleNotFoundError: No module named 'agents'` when running tests or scripts.
- **Fix**: Ensure virtual environment is activated (`source .venv/bin/activate`) and run tests with `pytest` or `python -m pytest`.

### Missing Environment Variable / API Key Error
- **Issue**: `ConfigurationError: Missing required Google GenAI API key`.
- **Fix**: Either set `GOOGLE_API_KEY` in `.env`, or run in simulation mode with `--simulate`.

### Test Failure
- **Issue**: `pytest` fails on async tests.
- **Fix**: Confirm `pytest-asyncio` is installed via `pip install -r requirements.txt`.

### GitHub Actions Failure
- **Issue**: Test job fails on GitHub Actions runner.
- **Fix**: Check step logs in the GitHub Actions tab. Ensure all dependencies are listed in `requirements.txt`.

---

## 14. Security

- Never commit `.env` or hardcode API keys into repository files.
- `.gitignore` is configured to exclude environment files (`.env*`), virtual environments (`.venv/`), and bytecode (`__pycache__/`).
- The `SelfDebuggingLoop` automatically sanitizes API keys and sensitive tokens from error tracebacks before creating error reports.
- All agent target routing is restricted to a strict allowlist (`owner`, `cs-agent`, `ads-agent`, `debugger-agent`) via `AgentRouter`.
